"""
GLM (Z.AI) provider implementation via Chat Completion API.

Uses the OpenAI-compatible endpoint at https://api.z.ai/api/paas/v4/chat/completions
to interact with Z.AI VLM models like GLM-5V-Turbo.
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


class GlmProvider(ModelProvider):
    """
    Provider for Z.AI VLM models (GLM-5V-Turbo, GLM-4.6V, etc.)
    via the OpenAI-compatible Chat Completion API.
    """

    name = "glm"
    ENDPOINT = "https://api.z.ai/api/paas/v4/chat/completions"

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 data URI."""
        from helpers.image_utils import encode_file, guess_mime_type

        return f"data:{guess_mime_type(image_path)};base64,{encode_file(image_path)}"

    def _extract_usage(self, response_body: dict) -> TokenUsage:
        """Extract token usage from Z.AI response."""
        usage = response_body.get("usage", {})
        if isinstance(usage, dict):
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        return TokenUsage()

    def _extract_content(self, response_body: dict, context: str = "") -> str | None:
        """Extract text content from a Z.AI response. Returns None if empty."""
        choices = response_body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderInvalidResponseError(
                f"GLM no devolvió choices para {context}",
                provider="glm",
            )
        first = choices[0]
        if not isinstance(first, dict):
            raise ProviderInvalidResponseError(
                f"Choice inválido para {context}",
                provider="glm",
            )
        message = first.get("message")
        if not isinstance(message, dict):
            raise ProviderInvalidResponseError(
                f"Message inválido para {context}",
                provider="glm",
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            return None
        return content

    def _call_api(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict, TokenUsage]:
        """Make a call to Z.AI Chat Completion API."""
        prompt_text = prompt
        use_json_mode = schema is not None

        if use_json_mode:
            # Inject schema description into the prompt so the model
            # knows the expected JSON structure (Z.AI json_object mode
            # requires the schema to be described in the conversation).
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
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": self._encode_image(image_path),
                            },
                        },
                        {"type": "text", "text": prompt_text},
                    ],
                }
            ],
            "temperature": 0.0,
            "max_tokens": max_tokens,
            # Disable thinking mode to avoid consuming output tokens in reasoning
            "thinking": {"type": "disabled"},
        }

        if use_json_mode:
            payload["response_format"] = {"type": "json_object"}

        body = self._make_request(payload, image_path.name)
        usage = self._extract_usage(body)
        content = self._extract_content(body, image_path.name)

        # If JSON mode returned empty content, retry without response_format
        if content is None and use_json_mode:
            retry_payload = {**payload}
            retry_payload.pop("response_format", None)
            body = self._make_request(retry_payload, image_path.name)
            retry_usage = self._extract_usage(body)
            usage.add(retry_usage)
            content = self._extract_content(body, image_path.name)

        if content is None:
            raise ProviderInvalidResponseError(
                f"GLM no devolvió contenido para {image_path.name}",
                provider="glm",
            )

        # Strip markdown code fences (```json ... ```) that GLM sometimes wraps around JSON
        stripped = content.strip()
        if stripped.startswith("```"):
            first_newline = stripped.index("\n") if "\n" in stripped else len(stripped)
            stripped = stripped[first_newline + 1:]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
            stripped = stripped.strip()

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            # Try the original content as fallback
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = {"raw_text": content}

        return parsed, usage

    def _make_request(self, payload: dict, context: str) -> dict:
        """Send a request to the Z.AI API and return the response body."""
        request = urllib.request.Request(
            self.ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
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
                    f"GLM API auth error ({exc.code}) en {context}",
                    provider="glm",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code == 429:
                raise ProviderRateLimitError(
                    f"GLM API rate limit en {context}",
                    provider="glm",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            elif exc.code >= 500:
                raise ProviderServerError(
                    f"GLM API server error ({exc.code}) en {context}",
                    provider="glm",
                    details={"http_status": exc.code, "response": detail[:500]},
                ) from exc
            else:
                raise ProviderInvalidResponseError(
                    f"GLM API error {exc.code} en {context}: {detail[:300]}",
                    provider="glm",
                    details={"http_status": exc.code},
                ) from exc
        except urllib.error.URLError as exc:
            raise ProviderConnectionError(
                f"No se pudo conectar con GLM en {context}: {exc}",
                provider="glm",
            ) from exc

    def structured_completion(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict[str, Any], TokenUsage]:
        """
        Perform a completion on an image.

        If schema is provided, uses JSON mode with schema hint in prompt.
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
