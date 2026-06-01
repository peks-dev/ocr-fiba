from __future__ import annotations

import json

from fastapi import HTTPException
from pydantic import ValidationError

from ocr_engine_api.errors import error_response
from ocr_engine_api.schemas import PipelineOptions
from ocr_engine_core.config.pipeline_config import PipelineConfig, SectionOverride


ALLOWED_UPLOAD_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def build_config(options: PipelineOptions) -> PipelineConfig:
    section_overrides = {
        name: SectionOverride(
            provider=override.provider,
            model=override.model,
            reasoning=override.reasoning,
            max_tokens=override.max_tokens,
        )
        for name, override in options.section_overrides.items()
    }
    return PipelineConfig(
        cropper_provider=options.cropper_provider,
        cropper_model=options.cropper_model,
        extractor_provider=options.extractor_provider,
        extractor_model=options.extractor_model,
        extractor_reasoning=options.extractor_reasoning,
        extractor_max_workers=options.extractor_max_workers,
        section_overrides=section_overrides,
        validation_plugins=options.validation_plugins,
        grid_removal=options.grid_removal,
        gamma=options.gamma,
    )


def parse_options_json(value: str | None) -> PipelineOptions:
    if not value:
        return PipelineOptions()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise error_response(400, "INVALID_OPTIONS_JSON", "options_json must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise error_response(400, "INVALID_OPTIONS_JSON", "options_json must be a JSON object")
    try:
        return PipelineOptions.model_validate(payload)
    except ValidationError as exc:
        raise error_response(
            400,
            "INVALID_PIPELINE_OPTIONS",
            "options_json does not match pipeline options schema",
            details={"errors": exc.errors()},
        ) from exc


def unsupported_upload_type_error() -> HTTPException:
    return error_response(
        400,
        "UNSUPPORTED_UPLOAD_TYPE",
        f"Upload extension must be one of: {', '.join(sorted(ALLOWED_UPLOAD_SUFFIXES))}",
    )
