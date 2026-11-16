"""
Interfaze provider implementation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ocr_engine_core.exceptions import ProviderInvalidResponseError
from .base import TokenUsage
from .http_base import HttpJsonProvider


class InterfazeProvider(HttpJsonProvider):
    """
    Provider for Interfaze API (https://interfaze.ai).
    """

    name = "interfaze"
    ENDPOINT = "https://api.interfaze.ai/v1/chat/completions"

    def _auth_headers(self) -> dict[str, str]:
        return {**super()._auth_headers(), "User-Agent": "ocr-lab/0.1"}

    def _extract_usage(self, response_body: dict) -> TokenUsage:
        """Interfaze sometimes nests usage under response.body."""
        usage = response_body.get("usage", {})
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

    def _call_api(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict[str, Any], TokenUsage]:
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
                                "file_data": self._encode_data_uri(image_path),
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
                "json_schema": {"name": "extraction", "schema": schema},
            }

        body = self._make_request(payload, image_path.name)
        usage = self._extract_usage(body)
        content = self._extract_openai_content(body, image_path.name)
        if content is None:
            raise ProviderInvalidResponseError(
                f"Interfaze no devolvió contenido para {image_path.name}",
                provider="interfaze",
            )

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and isinstance(parsed.get("object"), dict):
                parsed = parsed["object"]
        except json.JSONDecodeError:
            parsed = {"raw_text": content}

        return parsed, usage
