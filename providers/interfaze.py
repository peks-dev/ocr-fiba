"""
Interfaze provider implementation.
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


class InterfazeProvider(ModelProvider):
    """
    Provider for Interfaze API (https://interfaze.ai).
    """

    name = "interfaze"
    ENDPOINT = "https://api.interfaze.ai/v1/chat/completions"

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 data URI."""
        from helpers.image_utils import encode_file, guess_mime_type

        return f"data:{guess_mime_type(image_path)};base64,{encode_file(image_path)}"

    def _extract_usage(self, response_body: dict) -> TokenUsage:
        """Extract token usage from Interfaze response."""
        usage = response_body.get("usage", {})
        # Interfaze sometimes nests usage under response.body
        if not isinstance(usage, dict) or not usage:
            nested_body = response_body.get("response", {}).get("body")
            if isinstance(nested_body, dict):
                usage = nested_body.get("usage", {})
        if isinstance(usage, dict):
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        return TokenUsage()

    def _extract_content(self, response_body: dict, context: str = "") -> str:
        """Extract text content from an Interfaze response."""
        choices = response_body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderInvalidResponseError(
                f"Interfaze no devolvió choices para {context}",
                provider="interfaze",
            )
        first = choices[0]
        if not isinstance(first, dict):
            raise ProviderInvalidResponseError(
                f"Choice inválido para {context}",
                provider="interfaze",
            )
        message = first.get("message")
        if not isinstance(message, dict):
            raise ProviderInvalidResponseError(
                f"Message inválido para {context}",
                provider="interfaze",
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderInvalidResponseError(
                f"Interfaze no devolvió contenido para {context}",
                provider="interfaze",
            )
        return content

    def _call_api(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict, TokenUsage]:
        """Make a call to Interfaze API."""
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "file",
                            "file": {
                                "filename": image_path.name,
                                "file_data": self._encode_image(image_path),
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }

        if schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "extraction",
                    "schema": schema,
                },
            }

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
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 401 or exc.code == 403:
                raise ProviderAuthError(
                    f"Interfaze API auth error ({exc.code}) en {image_path.name}",
                    provider="interfaze",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code == 429:
                raise ProviderRateLimitError(
                    f"Interfaze API rate limit en {image_path.name}",
                    provider="interfaze",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code >= 500:
                raise ProviderServerError(
                    f"Interfaze API server error ({exc.code}) en {image_path.name}",
                    provider="interfaze",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            else:
                raise ProviderInvalidResponseError(
                    f"Interfaze API error {exc.code} en {image_path.name}: {detail[:300]}",
                    provider="interfaze",
                    details={"http_status": exc.code},
                ) from exc
        except urllib.error.URLError as exc:
            raise ProviderConnectionError(
                f"No se pudo conectar con Interfaze en {image_path.name}: {exc}",
                provider="interfaze",
            ) from exc

        usage = self._extract_usage(body)
        content = self._extract_content(body, image_path.name)

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and isinstance(parsed.get("object"), dict):
                parsed = parsed["object"]
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
        """
        Perform a completion on an image.

        If schema is provided, uses structured JSON output (response_format).
        If schema is None, allows free-form text output (e.g. Markdown).
        """
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

        # Handle both formats:
        # 1. Array format: {"sections": [...]}
        # 2. Single object: {"name": "...", "x_min": ..., ...}
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
