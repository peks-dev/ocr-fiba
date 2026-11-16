"""
OpenRouter provider implementation via Chat Completion API.

Uses OpenRouter's OpenAI-compatible endpoint for multimodal requests
and structured JSON output with JSON Schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ocr_engine_core.exceptions import ProviderInvalidResponseError
from .base import TokenUsage
from .http_base import HttpJsonProvider


class OpenrouterProvider(HttpJsonProvider):
    """Provider for OpenRouter-hosted models such as google/gemini-3-flash-preview."""

    name = "openrouter"
    ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model_name: str, api_key: str, reasoning: dict[str, Any] | None = None):
        super().__init__(model_name, api_key)
        self.reasoning = reasoning

    def _auth_headers(self) -> dict[str, str]:
        return {
            **super()._auth_headers(),
            "HTTP-Referer": "https://github.com/openai/codex",
            "X-OpenRouter-Title": "ocr-engine",
        }

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
                            "image_url": {"url": self._encode_data_uri(image_path)},
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
                "json_schema": {"name": "extraction", "strict": True, "schema": schema},
            }

        if self.reasoning:
            payload["reasoning"] = self.reasoning

        return payload

    def _call_api(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict[str, Any], TokenUsage]:
        use_json_mode = schema is not None
        payload = self._build_payload(image_path, prompt, schema, max_tokens, use_json_mode)
        body = self._make_request(payload, image_path.name)
        usage = self._extract_openai_usage(body)
        content = self._extract_openai_content(body, image_path.name)

        if content is None and use_json_mode:
            retry_payload = self._build_payload(image_path, prompt, schema, max_tokens, use_json_mode=False)
            body = self._make_request(retry_payload, image_path.name)
            usage.add(self._extract_openai_usage(body))
            content = self._extract_openai_content(body, image_path.name)

        if content is None:
            raise ProviderInvalidResponseError(
                f"OpenRouter no devolvió contenido para {image_path.name}",
                provider="openrouter",
            )

        return self._parse_json_or_raw(content), usage
