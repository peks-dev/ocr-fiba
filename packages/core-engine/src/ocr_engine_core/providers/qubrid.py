"""
Qubrid provider implementation via Chat Completion API.

Uses Qubrid's official chat completions endpoint with OpenAI-compatible
message formatting for multimodal requests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ocr_engine_core.exceptions import ProviderInvalidResponseError
from .base import TokenUsage
from .http_base import HttpJsonProvider


class QubridProvider(HttpJsonProvider):
    """
    Provider for Qubrid-hosted multimodal models such as Qwen/Qwen3-VL-Flash.
    """

    name = "qubrid"
    ENDPOINT = "https://platform.qubrid.com/v1/chat/completions"

    def _auth_headers(self) -> dict[str, str]:
        return {**super()._auth_headers(), "User-Agent": "ocr-lab/0.1"}

    @staticmethod
    def _extract_finish_reason(response_body: dict) -> str | None:
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
                        {"type": "image_url", "image_url": {"url": self._encode_data_uri(image_path)}},
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
        finish_reason = self._extract_finish_reason(body)

        should_retry_without_json_mode = content is None or finish_reason == "length"

        if should_retry_without_json_mode and use_json_mode:
            retry_payload = self._build_payload(image_path, prompt, schema, max_tokens, use_json_mode=False)
            body = self._make_request(retry_payload, image_path.name)
            usage.add(self._extract_openai_usage(body))
            content = self._extract_openai_content(body, image_path.name)
            finish_reason = self._extract_finish_reason(body)

        if content is None:
            raise ProviderInvalidResponseError(
                f"Qubrid no devolvió contenido para {image_path.name}",
                provider="qubrid",
            )

        stripped = self._strip_code_fences(content)
        try:
            parsed: dict[str, Any] | None = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None

        if parsed is None and use_json_mode:
            retry_payload = self._build_payload(image_path, prompt, schema, max_tokens, use_json_mode=False)
            body = self._make_request(retry_payload, image_path.name)
            usage.add(self._extract_openai_usage(body))
            content = self._extract_openai_content(body, image_path.name)
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
