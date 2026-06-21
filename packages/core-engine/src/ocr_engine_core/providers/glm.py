"""
GLM (Z.AI) provider implementation via Chat Completion API.

Uses the OpenAI-compatible endpoint at https://api.z.ai/api/paas/v4/chat/completions
to interact with Z.AI VLM models like GLM-5V-Turbo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ocr_engine_core.exceptions import ProviderInvalidResponseError
from .base import TokenUsage
from .http_base import HttpJsonProvider


class GlmProvider(HttpJsonProvider):
    """
    Provider for Z.AI VLM models (GLM-5V-Turbo, GLM-4.6V, etc.)
    via the OpenAI-compatible Chat Completion API.
    """

    name = "glm"
    ENDPOINT = "https://api.z.ai/api/paas/v4/chat/completions"

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
            # Z.AI json_object mode requires the schema described in the prompt.
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
                        {"type": "image_url", "image_url": {"url": self._encode_data_uri(image_path)}},
                        {"type": "text", "text": prompt_text},
                    ],
                }
            ],
            "temperature": 0.0,
            "max_tokens": max_tokens,
            # Disable thinking mode to avoid consuming output tokens in reasoning
            "thinking": {"type": "disabled"},
        }

        if schema is not None and use_json_mode:
            payload["response_format"] = {"type": "json_object"}

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

        # If JSON mode returned empty content, retry without response_format
        if content is None and use_json_mode:
            retry_payload = self._build_payload(image_path, prompt, schema, max_tokens, use_json_mode=False)
            body = self._make_request(retry_payload, image_path.name)
            usage.add(self._extract_openai_usage(body))
            content = self._extract_openai_content(body, image_path.name)

        if content is None:
            raise ProviderInvalidResponseError(
                f"GLM no devolvió contenido para {image_path.name}",
                provider="glm",
            )

        return self._parse_json_or_raw(content), usage
