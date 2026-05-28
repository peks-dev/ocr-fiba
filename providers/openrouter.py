"""
OpenRouter provider implementation via Chat Completion API.

Uses OpenRouter's OpenAI-compatible endpoint for multimodal requests
and structured JSON output with JSON Schema.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from core.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderServerError,
)
from .base import BoundingBox, ModelProvider, TokenUsage


class OpenrouterProvider(ModelProvider):
    """Provider for OpenRouter-hosted models such as google/gemini-3-flash-preview."""

    name = "openrouter"
    ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model_name: str, api_key: str, reasoning: dict[str, Any] | None = None):
        super().__init__(model_name, api_key)
        self.reasoning = reasoning

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 data URI."""
        from helpers.image_utils import encode_file, guess_mime_type

        return f"data:{guess_mime_type(image_path)};base64,{encode_file(image_path)}"

    def _extract_usage(self, response_body: dict) -> TokenUsage:
        """Extract token usage from OpenRouter response."""
        usage = response_body.get("usage", {})
        if isinstance(usage, dict):
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        return TokenUsage()

    def _extract_content(self, response_body: dict, context: str = "") -> str | None:
        """Extract text content from an OpenRouter response. Returns None if empty."""
        choices = response_body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderInvalidResponseError(
                f"OpenRouter no devolvió choices para {context}",
                provider="openrouter",
            )
        first = choices[0]
        if not isinstance(first, dict):
            raise ProviderInvalidResponseError(
                f"Choice inválido para {context}",
                provider="openrouter",
            )
        message = first.get("message")
        if not isinstance(message, dict):
            raise ProviderInvalidResponseError(
                f"Message inválido para {context}",
                provider="openrouter",
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            return None
        return content

    def _build_payload(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
        use_json_mode: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
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
        }

        if schema is not None and use_json_mode:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "extraction",
                    "strict": True,
                    "schema": schema,
                },
            }

        if self.reasoning:
            payload["reasoning"] = self.reasoning

        return payload

    def _make_request(self, payload: dict[str, Any], context: str) -> dict[str, Any]:
        """Send a request to OpenRouter and return the parsed response body."""
        request = urllib.request.Request(
            self.ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "HTTP-Referer": "https://github.com/openai/codex",
                "X-OpenRouter-Title": "ocr-engine",
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
                    f"OpenRouter API auth error ({exc.code}) en {context}",
                    provider="openrouter",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code == 429:
                raise ProviderRateLimitError(
                    f"OpenRouter API rate limit en {context}",
                    provider="openrouter",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code >= 500:
                raise ProviderServerError(
                    f"OpenRouter API server error ({exc.code}) en {context}",
                    provider="openrouter",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            else:
                raise ProviderInvalidResponseError(
                    f"OpenRouter API error {exc.code} en {context}: {detail[:300]}",
                    provider="openrouter",
                    details={"http_status": exc.code},
                ) from exc
        except urllib.error.URLError as exc:
            raise ProviderConnectionError(
                f"No se pudo conectar con OpenRouter en {context}: {exc}",
                provider="openrouter",
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
        """Make a call to OpenRouter Chat Completion API."""
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

        if content is None and use_json_mode:
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

        if content is None:
            raise ProviderInvalidResponseError(
                f"OpenRouter no devolvió contenido para {image_path.name}",
                provider="openrouter",
            )

        stripped = self._strip_code_fences(content)
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = {"raw_text": content}

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
