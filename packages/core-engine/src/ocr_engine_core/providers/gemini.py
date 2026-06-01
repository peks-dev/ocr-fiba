"""
Gemini provider implementation via Google Generative AI.
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
    ProviderTimeoutError,
)
from .base import BoundingBox, ModelProvider, TokenUsage


class GeminiProvider(ModelProvider):
    """
    Provider for Google Gemini models (via Google AI Studio).
    """

    name = "gemini"

    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name, api_key)
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        )

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to raw base64 (no data URI prefix for Gemini)."""
        from ocr_engine_core.utils.image_utils import encode_file

        return encode_file(image_path)

    def _extract_usage(self, response_body: dict) -> TokenUsage:
        """Extract token usage from Gemini response."""
        usage = response_body.get("usageMetadata", {})
        if isinstance(usage, dict):
            return TokenUsage(
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                total_tokens=usage.get("totalTokenCount", 0),
            )
        return TokenUsage()

    def _extract_text(self, response_body: dict, context: str = "") -> str:
        """Extract text content from a Gemini response."""
        candidates = response_body.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ProviderInvalidResponseError(
                f"Gemini no devolvió candidates para {context}",
                provider="gemini",
            )
        first = candidates[0]
        if not isinstance(first, dict):
            raise ProviderInvalidResponseError(
                f"Respuesta candidate inválida para {context}",
                provider="gemini",
            )
        content = first.get("content")
        if not isinstance(content, dict):
            raise ProviderInvalidResponseError(
                f"Respuesta content inválida para {context}",
                provider="gemini",
            )
        parts = content.get("parts")
        if not isinstance(parts, list):
            raise ProviderInvalidResponseError(
                f"Respuesta parts inválida para {context}",
                provider="gemini",
            )
        texts = [
            part.get("text")
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        if not texts:
            raise ProviderInvalidResponseError(
                f"Gemini no devolvió texto JSON para {context}",
                provider="gemini",
            )
        return "\n".join(texts)

    def _call_api(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict, TokenUsage]:
        """Make a call to Gemini API."""
        from ocr_engine_core.utils.image_utils import guess_mime_type

        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": guess_mime_type(image_path),
                                "data": self._encode_image(image_path),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": max_tokens,
            },
        }

        if schema is not None:
            payload["generationConfig"]["response_mime_type"] = "application/json"
            payload["generationConfig"]["response_schema"] = schema

        url = f"{self.endpoint}?key={self.api_key}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 401 or exc.code == 403:
                raise ProviderAuthError(
                    f"Gemini API auth error ({exc.code}) para {image_path.name}",
                    provider="gemini",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code == 429:
                raise ProviderRateLimitError(
                    f"Gemini API rate limit para {image_path.name}",
                    provider="gemini",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code >= 500:
                raise ProviderServerError(
                    f"Gemini API server error ({exc.code}) para {image_path.name}",
                    provider="gemini",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            else:
                raise ProviderInvalidResponseError(
                    f"Gemini API error {exc.code} para {image_path.name}: {detail[:300]}",
                    provider="gemini",
                    details={"http_status": exc.code},
                ) from exc
        except urllib.error.URLError as exc:
            raise ProviderConnectionError(
                f"No se pudo conectar con Gemini para {image_path.name}: {exc}",
                provider="gemini",
            ) from exc

        usage = self._extract_usage(body)
        text = self._extract_text(body, image_path.name)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Try to repair truncated JSON by closing open structures
            repaired = self._try_repair_json(text)
            if repaired is not None:
                parsed = repaired
            else:
                parsed = {"raw_text": text}

        return parsed, usage

    @staticmethod
    def _try_repair_json(text: str) -> dict | None:
        """Attempt to repair truncated JSON by removing incomplete values and closing structures."""
        import re
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")
        if open_braces <= 0 and open_brackets <= 0:
            return None

        cleaned = text.rstrip()
        # Remove trailing incomplete key-value pair (e.g. '"confidence": 0.8' cut mid-value)
        cleaned = re.sub(r',\s*"[^"]*"\s*:\s*[^,}\]]*$', '', cleaned)
        # Also handle number fragment at end
        cleaned = re.sub(r',\s*"[^"]*"\s*:\s*\d*\.?\d*$', '', cleaned)

        open_braces = cleaned.count("{") - cleaned.count("}")
        open_brackets = cleaned.count("[") - cleaned.count("]")
        repaired = cleaned + "]" * max(0, open_brackets) + "}" * max(0, open_braces)
        try:
            result = json.loads(repaired)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        return None

    def structured_completion(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict[str, Any], TokenUsage]:
        """
        Perform a completion on an image.

        If schema is provided, uses structured JSON output.
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
