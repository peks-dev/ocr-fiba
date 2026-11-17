from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, TypeVar

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from ocr_engine_api.errors import error_response
from ocr_engine_api.pipeline_options import build_config, parse_options_json, unsupported_upload_type_error
from ocr_engine_api.responses import sanitize_for_public_response
from ocr_engine_api.schemas import CreateRunRequest
from ocr_engine_api.settings import resolve_runs_dir
from ocr_engine_api.services.run_executor import RunExecutor
from ocr_engine_api.services.run_repository import RunRepository, RunRepositoryError
from ocr_engine_core.exceptions import OcrEngineError
from ocr_engine_core.types import RunContext

router = APIRouter(prefix="/v1/runs", tags=["runs"])
T = TypeVar("T")


@router.post("")
async def create_run(
    request: CreateRunRequest,
) -> dict:
    from ocr_engine_api.settings import get_api_settings

    if not get_api_settings().allow_path_input:
        raise error_response(
            403,
            "PATH_INPUT_DISABLED",
            "Server-side image paths are disabled on this deployment; use POST /v1/runs/upload",
        )
    image_path = _resolve_input_file(request.image_path)
    runs_dir = resolve_runs_dir(request.runs_dir)
    context = RunContext.create_run(image_path, runs_dir, run_id=request.run_id)
    repository = RunRepository(runs_dir)
    try:
        repository.reserve_run_dir(context.run_id)
    except RunRepositoryError as exc:
        raise error_response(exc.status_code, exc.code, exc.message) from exc
    context.ensure_dirs()
    status = repository.create_status(context.run_id, exist_ok=True)
    RunExecutor(repository).submit_full_pipeline(
        image_path,
        run_id=context.run_id,
        runs_dir=runs_dir,
        config=build_config(request.options),
    )
    return sanitize_for_public_response({"success": True, **status})


@router.post("/upload")
async def upload_and_create_run(
    file: Annotated[UploadFile, File()],
    run_id: Annotated[str | None, Form()] = None,
    runs_dir: Annotated[str, Form()] = "runs",
    options_json: Annotated[str | None, Form()] = None,
) -> dict:
    options = parse_options_json(options_json)
    filename = _safe_upload_filename(file.filename)
    resolved_runs_dir = resolve_runs_dir(runs_dir)
    context = RunContext.create_run(Path(filename), resolved_runs_dir, run_id=run_id)
    repository = RunRepository(resolved_runs_dir)
    try:
        repository.ensure_new_run_available(context.run_id)
    except RunRepositoryError as exc:
        raise error_response(exc.status_code, exc.code, exc.message) from exc

    from ocr_engine_api.settings import get_api_settings

    max_upload_mb = get_api_settings().max_upload_mb
    content = await _read_bounded_upload(file, max_upload_mb=max_upload_mb)
    _validate_image_magic_bytes(content)

    try:
        repository.reserve_run_dir(context.run_id)
    except RunRepositoryError as exc:
        raise error_response(exc.status_code, exc.code, exc.message) from exc

    context.ensure_dirs()
    input_path = context.input_dir / filename
    input_path.write_bytes(content)

    status = repository.create_status(context.run_id, exist_ok=True)
    RunExecutor(repository).submit_full_pipeline(
        input_path,
        run_id=context.run_id,
        runs_dir=resolved_runs_dir,
        config=build_config(options),
    )
    return sanitize_for_public_response({"success": True, **status})


@router.get("")
async def list_runs(
    runs_dir: Annotated[str, Query()] = "runs",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.list_runs(limit=limit),
    )


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    runs_dir: str = Query(default="runs"),
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.get_run(run_id),
    )


@router.delete("/{run_id}")
async def delete_run(
    run_id: str,
    runs_dir: Annotated[str, Query()] = "runs",
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.delete_run(run_id),
    )


@router.get("/{run_id}/trace")
async def get_run_trace(
    run_id: str,
    runs_dir: str = Query(default="runs"),
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.get_trace(run_id),
    )


@router.get("/{run_id}/result")
async def get_run_result(
    run_id: str,
    runs_dir: str = Query(default="runs"),
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.get_result(run_id),
    )


@router.get("/{run_id}/artifacts")
async def list_run_artifacts(
    run_id: str,
    runs_dir: Annotated[str, Query()] = "runs",
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.list_artifacts(run_id, limit=limit),
    )


@router.get("/{run_id}/artifacts/{name:path}", response_class=FileResponse)
async def get_run_artifact(
    run_id: str,
    name: str,
    runs_dir: str = Query(default="runs"),
) -> FileResponse:
    artifact_path = _run_repository_call(
        runs_dir,
        lambda repository: repository.resolve_artifact(run_id, name),
    )
    return FileResponse(artifact_path)


def _run_repository_call(runs_dir: str, callback: Callable[[RunRepository], T]) -> T:
    try:
        return sanitize_for_public_response(callback(RunRepository(resolve_runs_dir(runs_dir))))
    except RunRepositoryError as exc:
        raise error_response(exc.status_code, exc.code, exc.message) from exc
    except OcrEngineError as exc:
        raise error_response(500, exc.code, exc.message, retryable=exc.retryable) from exc


def _resolve_input_file(value: str) -> Path:
    image_path = Path(value).expanduser().resolve()
    if not image_path.exists():
        raise error_response(404, "INPUT_IMAGE_NOT_FOUND", f"Input image not found: {image_path}")
    if not image_path.is_file():
        raise error_response(400, "INPUT_IMAGE_INVALID", f"Input path is not a file: {image_path}")
    return image_path


def _safe_upload_filename(filename: str | None) -> str:
    name = Path(filename or "upload.jpg").name
    suffix = Path(name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise unsupported_upload_type_error()
    return name


_UPLOAD_CHUNK_BYTES = 65_536


async def _read_bounded_upload(file: UploadFile, *, max_upload_mb: int) -> bytes:
    """Read an UploadFile without exceeding max_upload_mb in memory."""
    max_upload_bytes = max_upload_mb * 1024 * 1024
    declared_size = getattr(file, "size", None)
    if isinstance(declared_size, int) and declared_size > max_upload_bytes:
        raise error_response(
            413,
            "UPLOAD_TOO_LARGE",
            f"Uploaded file exceeds {max_upload_mb} MB limit",
        )

    chunks: list[bytes] = []
    total = 0
    while True:
        try:
            chunk = await file.read(_UPLOAD_CHUNK_BYTES)
        except TypeError:
            chunk = await file.read()
            if not chunk:
                break
            total += len(chunk)
            if total > max_upload_bytes:
                raise error_response(
                    413,
                    "UPLOAD_TOO_LARGE",
                    f"Uploaded file exceeds {max_upload_mb} MB limit",
                )
            chunks.append(chunk)
            break

        if not chunk:
            break
        total += len(chunk)
        if total > max_upload_bytes:
            raise error_response(
                413,
                "UPLOAD_TOO_LARGE",
                f"Uploaded file exceeds {max_upload_mb} MB limit",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content:
        raise error_response(400, "EMPTY_UPLOAD", "Uploaded file is empty")
    return content


def _validate_image_magic_bytes(content: bytes) -> None:
    """Ensure uploaded bytes match a supported image file signature (JPEG, PNG, WebP)."""
    is_jpeg = content.startswith(b"\xff\xd8\xff")
    is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if not (is_jpeg or is_png or is_webp):
        raise error_response(
            400,
            "INVALID_IMAGE_CONTENT",
            "Uploaded file content is not a valid JPEG, PNG, or WebP image",
        )
