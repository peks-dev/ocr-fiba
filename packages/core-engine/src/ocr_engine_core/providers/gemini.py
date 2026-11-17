"""
Gemini provider implementation via Google Generative AI.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ocr_engine_core.exceptions import ProviderInvalidResponseError
from .base import TokenUsage
from .http_base import HttpJsonProvider


class GeminiProvider(HttpJsonProvider):
    """
    Provider for Google Gemini models (via Google AI Studio).
    """

    name = "gemini"

    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name, api_key)
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        )

    # Gemini authenticates via the x-goog-api-key header so the secret never leaks in URLs.
    def _auth_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def _request_url(self) -> str:
        return self.endpoint

    def _extract_usage(self, response_body: dict) -> TokenUsage:
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
    ) -> tuple[dict[str, Any], TokenUsage]:
        from ocr_engine_core.utils.image_utils import guess_mime_type

        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": guess_mime_type(image_path),
                                "data": self._encode_base64(image_path),
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

        body = self._make_request(payload, image_path.name)
        usage = self._extract_usage(body)
        text = self._extract_text(body, image_path.name)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Try to repair truncated JSON by closing open structures
            repaired = self._try_repair_json(text)
            parsed = repaired if repaired is not None else {"raw_text": text}

        return parsed, usage

    @staticmethod
    def _try_repair_json(text: str) -> dict | None:
        """Attempt to repair truncated JSON by removing incomplete values and closing structures."""
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
