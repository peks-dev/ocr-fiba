from __future__ import annotations

import json

from fastapi import HTTPException
from pydantic import ValidationError

from ocr_engine_api.errors import error_response
from ocr_engine_api.schemas import PipelineOptions
from ocr_engine_core.config.pipeline_config import (
    PipelineConfig,
    SectionOverride,
    resolve_default_extractor_reasoning,
)


ALLOWED_UPLOAD_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def apply_server_defaults(options: PipelineOptions) -> PipelineOptions:
    """Fill extractor provider/model/reasoning from server env when the client did not set them.

    Lets a deployment (e.g. without DOCSTRANGE_API_KEY) pick a working default extractor
    via OCR_DEFAULT_EXTRACTOR_PROVIDER / OCR_DEFAULT_EXTRACTOR_MODEL /
    OCR_DEFAULT_EXTRACTOR_REASONING.
    """
    from ocr_engine_api.settings import get_api_settings

    settings = get_api_settings()
    updates: dict[str, object] = {}
    provider_set = "extractor_provider" in options.model_fields_set
    model_set = "extractor_model" in options.model_fields_set
    reasoning_set = "extractor_reasoning" in options.model_fields_set

    if settings.default_extractor_provider and not provider_set:
        updates["extractor_provider"] = settings.default_extractor_provider
    if settings.default_extractor_model and not provider_set and not model_set:
        updates["extractor_model"] = settings.default_extractor_model

    if not reasoning_set:
        effective_provider = str(updates.get("extractor_provider", options.extractor_provider))
        effective_model = str(updates.get("extractor_model", options.extractor_model))
        use_env = not provider_set and not model_set
        if use_env and settings.default_extractor_reasoning is not None:
            updates["extractor_reasoning"] = resolve_default_extractor_reasoning(
                effective_provider,
                effective_model,
                from_env=True,
                env_value=settings.default_extractor_reasoning,
            )
        else:
            updates["extractor_reasoning"] = resolve_default_extractor_reasoning(
                effective_provider,
                effective_model,
                from_env=False,
            )

    if not updates:
        return options
    return PipelineOptions.model_validate({**options.model_dump(exclude_unset=True), **updates})


def build_config(options: PipelineOptions) -> PipelineConfig:
    options = apply_server_defaults(options)
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
