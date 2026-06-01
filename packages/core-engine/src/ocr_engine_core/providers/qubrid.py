"""
Qubrid provider implementation via Chat Completion API.

Uses Qubrid's official chat completions endpoint with OpenAI-compatible
message formatting for multimodal requests.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from ocr_engine_core.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderServerError,
)
from .base import BoundingBox, ModelProvider, TokenUsage


class QubridProvider(ModelProvider):
    """
    Provider for Qubrid-hosted multimodal models such as Qwen/Qwen3-VL-Flash.
    """

    name = "qubrid"
    ENDPOINT = "https://platform.qubrid.com/v1/chat/completions"

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 data URI."""
        from ocr_engine_core.utils.image_utils import encode_file, guess_mime_type

        return f"data:{guess_mime_type(image_path)};base64,{encode_file(image_path)}"

    def _extract_usage(self, response_body: dict) -> TokenUsage:
        """Extract token usage from Qubrid response."""
        usage = response_body.get("usage", {})
        if isinstance(usage, dict):
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        return TokenUsage()

    def _extract_content(self, response_body: dict, context: str = "") -> str | None:
        """Extract text content from a Qubrid response. Returns None if empty."""
        choices = response_body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderInvalidResponseError(
                f"Qubrid no devolvió choices para {context}",
                provider="qubrid",
            )
        first = choices[0]
        if not isinstance(first, dict):
            raise ProviderInvalidResponseError(
                f"Choice inválido para {context}",
                provider="qubrid",
            )
        message = first.get("message")
        if not isinstance(message, dict):
            raise ProviderInvalidResponseError(
                f"Message inválido para {context}",
                provider="qubrid",
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            return None
        return content

    def _extract_finish_reason(self, response_body: dict) -> str | None:
        """Extract the first choice finish reason, if present."""
        choices = response_body.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first = choices[0]
        if not isinstance(first, dict):
            return None
        finish_reason = first.get("finish_reason")
        return finish_reason if isinstance(finish_reason, str) else None

    def _build_payload(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
        use_json_mode: bool = True,
    ) -> dict[str, Any]:
        prompt_text = prompt
        if schema is not None:
            prompt_text += (
                "\n\nResponde ÚNICAMENTE con un JSON válido que siga este schema:\n"
                + json.dumps(schema, indent=2, ensure_ascii=False)
            )

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": self._encode_image(image_path),
                            },
                        },
                    ],
                }
            ],
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "stream": False,
            "top_p": 1,
        }

        if schema is not None and use_json_mode:
            payload["response_format"] = {"type": "json_object"}

        return payload

    def _make_request(self, payload: dict[str, Any], context: str) -> dict[str, Any]:
        """Send a request to the Qubrid API and return the parsed JSON body."""
        request = urllib.request.Request(
            self.ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "ocr-lab/0.1",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 401 or exc.code == 403:
                raise ProviderAuthError(
                    f"Qubrid API auth error ({exc.code}) en {context}",
                    provider="qubrid",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code == 429:
                raise ProviderRateLimitError(
                    f"Qubrid API rate limit en {context}",
                    provider="qubrid",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code >= 500:
                raise ProviderServerError(
                    f"Qubrid API server error ({exc.code}) en {context}",
                    provider="qubrid",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            else:
                raise ProviderInvalidResponseError(
                    f"Qubrid API error {exc.code} en {context}: {detail[:300]}",
                    provider="qubrid",
                    details={"http_status": exc.code},
                ) from exc
        except urllib.error.URLError as exc:
            raise ProviderConnectionError(
                f"No se pudo conectar con Qubrid en {context}: {exc}",
                provider="qubrid",
            ) from exc

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        """Strip markdown code fences commonly wrapped around JSON."""
        stripped = content.strip()
        if stripped.startswith("```"):
            first_newline = stripped.index("\n") if "\n" in stripped else len(stripped)
            stripped = stripped[first_newline + 1:]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
        return stripped.strip()

    def _call_api(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict[str, Any], TokenUsage]:
        """Make a call to the Qubrid Chat Completion API."""
        use_json_mode = schema is not None
        payload = self._build_payload(
            image_path=image_path,
            prompt=prompt,
            schema=schema,
            max_tokens=max_tokens,
            use_json_mode=use_json_mode,
        )

        body = self._make_request(payload, image_path.name)
        usage = self._extract_usage(body)
        content = self._extract_content(body, image_path.name)
        finish_reason = self._extract_finish_reason(body)

        should_retry_without_json_mode = content is None or finish_reason == "length"

        if should_retry_without_json_mode and use_json_mode:
            retry_payload = self._build_payload(
                image_path=image_path,
                prompt=prompt,
                schema=schema,
                max_tokens=max_tokens,
                use_json_mode=False,
            )
            body = self._make_request(retry_payload, image_path.name)
            retry_usage = self._extract_usage(body)
            usage.add(retry_usage)
            content = self._extract_content(body, image_path.name)
            finish_reason = self._extract_finish_reason(body)

        if content is None:
            raise ProviderInvalidResponseError(
                f"Qubrid no devolvió contenido para {image_path.name}",
                provider="qubrid",
            )

        stripped = self._strip_code_fences(content)
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None

        if parsed is None and use_json_mode:
            retry_payload = self._build_payload(
                image_path=image_path,
                prompt=prompt,
                schema=schema,
                max_tokens=max_tokens,
                use_json_mode=False,
            )
            body = self._make_request(retry_payload, image_path.name)
            retry_usage = self._extract_usage(body)
            usage.add(retry_usage)
            content = self._extract_content(body, image_path.name)
            finish_reason = self._extract_finish_reason(body)
            if content is None:
                raise ProviderInvalidResponseError(
                    f"Qubrid no devolvió contenido para {image_path.name}",
                    provider="qubrid",
                )
            stripped = self._strip_code_fences(content)
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None

        if parsed is None:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = {"raw_text": content, "finish_reason": finish_reason}

        return parsed, usage

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

        boxes: list[BoundingBox] = []
        sections = result.get("sections", [])
        if not sections and isinstance(result, dict) and "x_min" in result:
            sections = [result]

        for section in sections:
            try:
                box = BoundingBox(
                    name=section["name"],
                    x_min=int(section["x_min"]),
                    y_min=int(section["y_min"]),
                    x_max=int(section["x_max"]),
                    y_max=int(section["y_max"]),
                    confidence=section.get("confidence"),
                )
                boxes.append(box)
            except (KeyError, ValueError, TypeError):
                continue

        return boxes, usage
