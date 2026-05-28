"""
DocStrange (Nanonets) provider implementation via Document Extraction API.

Uses the extraction-api.nanonets.com endpoint to interact with
Nanonets' OCR models (nanonets-ocr-3, ocr2+) for document extraction
with custom instructions and JSON schema support.

Key insight: When a JSON schema is passed via json_options, DocStrange
tends to hallucinate data to fill the schema. For best results on complex
sections like progressive_score, use output_format=json WITHOUT a schema
and let the model extract naturally.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

from core.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)
from .base import BoundingBox, ModelProvider, TokenUsage


class DocstrangeProvider(ModelProvider):
    """
    Provider for Nanonets DocStrange document extraction API.

    Supports custom_instructions (up to 8000 chars) with prompt_mode=replace
    for full prompt control, and json_options for structured JSON output
    with field lists or JSON schemas.
    """

    name = "docstrange"
    ENDPOINT = "https://extraction-api.nanonets.com/api/v1/extract/sync"
    MAX_RETRIES = 3

    def _call_api(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
        agentic_mode: bool = False,
    ) -> tuple[dict, TokenUsage]:
        """Make a call to DocStrange Extraction API using requests library."""
        data: dict[str, Any] = {
            "output_format": "json",
            "custom_instructions": prompt,
            "prompt_mode": "replace",
        }

        if schema is not None:
            data["json_options"] = json.dumps(schema, ensure_ascii=False)

        if agentic_mode:
            data["agentic_mode"] = "true"

        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                with open(image_path, "rb") as f:
                    response = requests.post(
                        self.ENDPOINT,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        files={"file": f},
                        data=data,
                        timeout=300,
                    )
                response.raise_for_status()
                resp_body = response.json()
                break
            except requests.exceptions.HTTPError as exc:
                status_code = exc.response.status_code if exc.response else 0
                detail = exc.response.text if exc.response else str(exc)
                if status_code == 429 and attempt < self.MAX_RETRIES:
                    time.sleep(2 ** attempt * 5)
                    last_error = exc
                    continue
                if status_code in (401, 403):
                    raise ProviderAuthError(
                        f"DocStrange API auth error ({status_code}) en {image_path.name}",
                        provider="docstrange",
                        details={"http_status": status_code, "response": detail[:500]},
                    ) from exc
                elif status_code == 429:
                    raise ProviderRateLimitError(
                        f"DocStrange API rate limit en {image_path.name}",
                        provider="docstrange",
                        details={"http_status": status_code, "response": detail[:500]},
                    ) from exc
                elif status_code >= 500:
                    raise ProviderServerError(
                        f"DocStrange API server error ({status_code}) en {image_path.name}",
                        provider="docstrange",
                        details={"http_status": status_code, "response": detail[:500]},
                    ) from exc
                else:
                    raise ProviderInvalidResponseError(
                        f"DocStrange API error {status_code} en {image_path.name}: {detail[:300]}",
                        provider="docstrange",
                        details={"http_status": status_code},
                    ) from exc
            except requests.exceptions.Timeout as exc:
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    time.sleep(2 ** attempt * 5)
                    continue
                raise ProviderTimeoutError(
                    f"DocStrange API timeout en {image_path.name}",
                    provider="docstrange",
                ) from exc
            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    time.sleep(2 ** attempt * 5)
                    continue
                raise ProviderConnectionError(
                    f"No se pudo conectar con DocStrange en {image_path.name}: {exc}",
                    provider="docstrange",
                ) from exc
        else:
            raise ProviderConnectionError(
                f"No se pudo conectar con DocStrange en {image_path.name}: {last_error}",
                provider="docstrange",
            )

        usage = self._extract_usage(resp_body)
        parsed = self._parse_response(resp_body)

        return parsed, usage

    def _extract_usage(self, response_body: dict) -> TokenUsage:
        """Extract token usage from DocStrange response."""
        usage = response_body.get("usage", {})
        if isinstance(usage, dict):
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        result = response_body.get("result", {})
        if isinstance(result, dict):
            usage = result.get("usage", {})
            if isinstance(usage, dict):
                return TokenUsage(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                )
        return TokenUsage()

    def _parse_response(self, resp_body: dict) -> dict:
        """Parse the DocStrange API response into a structured dict."""
        result = resp_body.get("result", {})

        if not isinstance(result, dict):
            return {"raw_text": json.dumps(resp_body, ensure_ascii=False)}

        # JSON output: data is under result.json.content
        json_data = result.get("json", {})
        if isinstance(json_data, dict):
            content = json_data.get("content")
            if isinstance(content, dict):
                return _unwrap_docstrange_content(content)
            if json_data and not json_data.get("metadata"):
                return _unwrap_docstrange_content(json_data)

        # Markdown output: data is under result.markdown.content
        md_data = result.get("markdown", {})
        if isinstance(md_data, dict):
            content = md_data.get("content", "")
            if isinstance(content, str) and content.strip():
                return {"raw_text": content}

        # Fallback: try to extract any text content
        for key in ("content", "text", "markdown", "html"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return {"raw_text": val}
            if isinstance(val, dict):
                inner = val.get("content", "")
                if isinstance(inner, str) and inner.strip():
                    return {"raw_text": inner}

        return {"raw_text": json.dumps(resp_body, ensure_ascii=False)}

    def structured_completion(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
        agentic_mode: bool = False,
    ) -> tuple[dict[str, Any], TokenUsage]:
        """
        Perform a completion on an image.

        If schema is provided, uses JSON output with json_options schema.
        If schema is None, uses JSON output without schema (free-form).
        If agentic_mode is True, enables post-processing for consistent output.
        """
        return self._call_api(image_path, prompt, schema, max_tokens, agentic_mode=agentic_mode)

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


def _unwrap_docstrange_content(content: dict[str, Any]) -> dict[str, Any]:
    """Unwrap DocStrange's descriptive wrapper keys.

    When no schema is provided, DocStrange wraps the extracted data in a
    descriptive key (e.g. "anotacion_progresiva": {...}) instead of returning
    the data directly. This function unwraps such single-key wrappers.

    If the content has the expected keys (team_a, team_b, etc.), return as-is.
    If it has a single wrapper key containing a dict, unwrap it.
    """
    pipeline_keys = {
        "team_a", "team_b", "sections", "league", "tournament", "date", "time",
        "final_score", "winner", "quarters", "team_fouls_quarters",
        "name", "captain", "players", "entries",
    }
    if any(key in content for key in pipeline_keys):
        return content

    dict_values = [(k, v) for k, v in content.items() if isinstance(v, dict)]
    if len(dict_values) == 1:
        return dict_values[0][1]

    for key, value in dict_values:
        if isinstance(value, dict) and any(k in value for k in pipeline_keys):
            return value

    return content
