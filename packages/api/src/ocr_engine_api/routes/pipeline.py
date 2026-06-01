from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import ValidationError

from ocr_engine_api.errors import engine_error_response, error_response
from ocr_engine_api.responses import sanitize_for_public_response
from ocr_engine_api.schemas import PipelineOptions, RunFullPipelineRequest
from ocr_engine_api.settings import get_api_settings, resolve_runs_dir
from ocr_engine_core.config.pipeline_config import PipelineConfig, SectionOverride
from ocr_engine_core.exceptions import OcrEngineError
from ocr_engine_core.toolbox import OcrToolbox

router = APIRouter(prefix="/v1/pipeline", tags=["pipeline"])
ALLOWED_UPLOAD_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@router.post("/full")
async def run_full_pipeline(request: RunFullPipelineRequest) -> dict:
    image_path = _resolve_input_file(request.image_path)

    try:
        runs_dir = resolve_runs_dir(request.runs_dir)
        toolbox = OcrToolbox(_build_config(request.options))
        result = toolbox.run_full_pipeline(
            image_path,
            run_id=request.run_id,
            runs_dir=runs_dir,
            use_run_layout=True,
        )
        return sanitize_for_public_response(result.to_dict())
    except OcrEngineError as exc:
        raise engine_error_response(exc) from exc
    except ValueError as exc:
        raise error_response(400, "INVALID_PIPELINE_REQUEST", str(exc)) from exc


@router.post("/full/upload")
async def upload_and_run_full_pipeline(
    file: Annotated[UploadFile, File()],
    run_id: Annotated[str | None, Form()] = None,
    runs_dir: Annotated[str, Form()] = "runs",
    options_json: Annotated[str | None, Form()] = None,
) -> dict:
    options = _parse_options_json(options_json)
    filename = _safe_upload_filename(file.filename)

    try:
        resolved_runs_dir = resolve_runs_dir(runs_dir)
        content = await file.read()
        if not content:
            raise error_response(400, "EMPTY_UPLOAD", "Uploaded file is empty")
        max_upload_mb = get_api_settings().max_upload_mb
        max_upload_bytes = max_upload_mb * 1024 * 1024
        if len(content) > max_upload_bytes:
            raise error_response(
                413,
                "UPLOAD_TOO_LARGE",
                f"Uploaded file exceeds {max_upload_mb} MB limit",
            )

        toolbox = OcrToolbox(_build_config(options))
        context = toolbox.create_context(
            Path(filename),
            run_id=run_id,
            runs_dir=resolved_runs_dir,
            use_run_layout=True,
        )
        context.ensure_dirs()
        input_path = context.input_dir / filename
        input_path.write_bytes(content)
        result = toolbox.run_full_pipeline(
            input_path,
            run_id=context.run_id,
            runs_dir=resolved_runs_dir,
            use_run_layout=True,
        )
        return sanitize_for_public_response(result.to_dict())
    except OcrEngineError as exc:
        raise engine_error_response(exc) from exc
    except ValueError as exc:
        raise error_response(400, "INVALID_PIPELINE_REQUEST", str(exc)) from exc


def _build_config(options: PipelineOptions) -> PipelineConfig:
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


def _resolve_input_file(value: str) -> Path:
    image_path = Path(value).expanduser().resolve()
    if not image_path.exists():
        raise error_response(404, "INPUT_IMAGE_NOT_FOUND", f"Input image not found: {image_path}")
    if not image_path.is_file():
        raise error_response(400, "INPUT_IMAGE_INVALID", f"Input path is not a file: {image_path}")
    return image_path


def _parse_options_json(value: str | None) -> PipelineOptions:
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


def _safe_upload_filename(filename: str | None) -> str:
    name = Path(filename or "upload.jpg").name
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise error_response(
            400,
            "UNSUPPORTED_UPLOAD_TYPE",
            f"Upload extension must be one of: {', '.join(sorted(ALLOWED_UPLOAD_SUFFIXES))}",
        )
    return name
