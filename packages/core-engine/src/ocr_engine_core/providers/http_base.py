"""
Shared HTTP/JSON provider base.

Centralizes everything the chat-completion-style providers had copy-pasted:
image encoding, the urllib POST with HTTP-error → typed-exception mapping,
**retry with exponential backoff + jitter** on retryable errors, JSON parsing
with code-fence stripping, OpenAI-style content/usage extraction, and the
(identical) ``detect_bounding_boxes`` / ``structured_completion`` surface.

Concrete providers only implement ``_call_api`` (provider-specific payload and
response parsing) and, when needed, override ``_auth_headers`` / ``_request_url``.
"""

from __future__ import annotations

import json
import random
import socket
import time
import urllib.error
import urllib.request
from abc import abstractmethod
from pathlib import Path
from typing import Any

from ocr_engine_core.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)
from .base import BoundingBox, ModelProvider, TokenUsage


class HttpJsonProvider(ModelProvider):
    """Base for providers that POST JSON and parse a JSON/text response."""

    # Subclasses set these.
    ENDPOINT: str = ""

    # --- Network + retry policy (shared across providers) -------------------
    TIMEOUT: int = 180
    MAX_ATTEMPTS: int = 4          # 1 initial try + up to 3 retries
    BACKOFF_BASE: float = 1.0      # seconds
    BACKOFF_CAP: float = 20.0      # seconds
    BACKOFF_JITTER: float = 0.25   # fraction of the delay added as jitter

    # ------------------------------------------------------------------ HTTP

    def _auth_headers(self) -> dict[str, str]:
        """Default OpenAI-compatible auth headers. Override as needed."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request_url(self) -> str:
        """URL to POST to. Override for providers that key in the query string."""
        return self.ENDPOINT

    def _make_request(self, payload: dict[str, Any], context: str) -> dict[str, Any]:
        """POST ``payload`` and return the parsed JSON body, with retries."""
        return self._post_json(self._request_url(), payload, self._auth_headers(), context)

    def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        context: str,
    ) -> dict[str, Any]:
        """POST with exponential backoff + jitter on retryable provider errors."""
        attempt = 0
        while True:
            try:
                return self._post_once(url, payload, headers, context)
            except ProviderError as exc:
                attempt += 1
                if not exc.retryable or attempt >= self.MAX_ATTEMPTS:
                    raise
                self._sleep_backoff(attempt)

    def _post_once(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        context: str,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise self._http_error(exc.code, context, detail) from exc
        except (socket.timeout, TimeoutError) as exc:
            raise ProviderTimeoutError(
                f"Timeout llamando a {self.name} en {context}",
                provider=self.name,
            ) from exc
        except urllib.error.URLError as exc:
            # A read timeout can surface wrapped in URLError too.
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise ProviderTimeoutError(
                    f"Timeout llamando a {self.name} en {context}",
                    provider=self.name,
                ) from exc
            raise ProviderConnectionError(
                f"No se pudo conectar con {self.name} en {context}: {exc}",
                provider=self.name,
            ) from exc

    def _http_error(self, status: int, context: str, detail: str) -> ProviderError:
        """Map an HTTP status code to a typed provider exception."""
        if status in (401, 403):
            return ProviderAuthError(
                f"{self.name} API auth error ({status}) en {context}",
                provider=self.name,
                details={"http_status": status, "response": detail[:500]},
            )
        if status == 429:
            return ProviderRateLimitError(
                f"{self.name} API rate limit en {context}",
                provider=self.name,
                details={"http_status": status, "response": detail[:500]},
            )
        if status >= 500:
            return ProviderServerError(
                f"{self.name} API server error ({status}) en {context}",
                provider=self.name,
                details={"http_status": status, "response": detail[:500]},
            )
        return ProviderInvalidResponseError(
            f"{self.name} API error {status} en {context}: {detail[:300]}",
            provider=self.name,
            details={"http_status": status},
        )

    def _sleep_backoff(self, attempt: int) -> None:
        """Sleep ``BACKOFF_BASE * 2**(attempt-1)`` (capped) plus jitter."""
        delay = min(self.BACKOFF_CAP, self.BACKOFF_BASE * (2 ** (attempt - 1)))
        delay += random.uniform(0, delay * self.BACKOFF_JITTER)
        time.sleep(delay)

    # ---------------------------------------------------------------- encoding

    @staticmethod
    def _encode_data_uri(image_path: Path) -> str:
        """Encode an image as a base64 ``data:`` URI."""
        from ocr_engine_core.utils.image_utils import encode_file, guess_mime_type

        return f"data:{guess_mime_type(image_path)};base64,{encode_file(image_path)}"

    @staticmethod
    def _encode_base64(image_path: Path) -> str:
        """Encode an image as raw base64 (no data URI prefix)."""
        from ocr_engine_core.utils.image_utils import encode_file

        return encode_file(image_path)

    # ----------------------------------------------------------------- parsing

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        """Strip markdown code fences (```json ... ```) wrapped around JSON."""
        stripped = content.strip()
        if stripped.startswith("```"):
            first_newline = stripped.index("\n") if "\n" in stripped else len(stripped)
            stripped = stripped[first_newline + 1:]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
        return stripped.strip()

    def _parse_json_or_raw(self, content: str) -> dict[str, Any]:
        """Parse content as JSON, tolerating code fences; fall back to raw_text."""
        stripped = self._strip_code_fences(content)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"raw_text": content}

    def _extract_openai_usage(self, response_body: dict) -> TokenUsage:
        """Extract usage from an OpenAI-compatible ``usage`` object."""
        usage = response_body.get("usage", {})
        if isinstance(usage, dict):
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        return TokenUsage()

    def _extract_openai_content(self, response_body: dict, context: str = "") -> str | None:
        """Extract ``choices[0].message.content`` from an OpenAI-style response.

        Returns None when the content is missing/empty so callers can decide
        whether to retry without JSON mode.
        """
        choices = response_body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderInvalidResponseError(
                f"{self.name} no devolvió choices para {context}",
                provider=self.name,
            )
        first = choices[0]
        if not isinstance(first, dict):
            raise ProviderInvalidResponseError(
                f"Choice inválido para {context}",
                provider=self.name,
            )
        message = first.get("message")
        if not isinstance(message, dict):
            raise ProviderInvalidResponseError(
                f"Message inválido para {context}",
                provider=self.name,
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            return None
        return content

    # ----------------------------------------------------------- public surface

    @abstractmethod
    def _call_api(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict[str, Any], TokenUsage]:
        """Provider-specific request + response parsing."""
        ...

    def structured_completion(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict[str, Any], TokenUsage]:
        return self._call_api(image_path, prompt, schema, max_tokens)

    def detect_bounding_boxes(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int = 2000,
    ) -> tuple[list[BoundingBox], TokenUsage]:
        result, usage = self._call_api(image_path, prompt, schema, max_tokens)
        return self._parse_boxes(result), usage

    @staticmethod
    def _parse_boxes(result: dict[str, Any]) -> list[BoundingBox]:
        """Parse bounding boxes from a detection response.

        Accepts both the array form ``{"sections": [...]}`` and a single-object
        form ``{"name": ..., "x_min": ...}``.
        """
        boxes: list[BoundingBox] = []
        sections = result.get("sections", []) if isinstance(result, dict) else []
        if not sections and isinstance(result, dict) and "x_min" in result:
            sections = [result]

        for section in sections:
            try:
                boxes.append(
                    BoundingBox(
                        name=section["name"],
                        x_min=int(section["x_min"]),
                        y_min=int(section["y_min"]),
                        x_max=int(section["x_max"]),
                        y_max=int(section["y_max"]),
                        confidence=section.get("confidence"),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        return boxes
