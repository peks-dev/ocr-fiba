from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from api.errors import error_response

router = APIRouter(prefix="/v1/runs", tags=["runs"])


@router.get("/{run_id}")
def get_run(
    run_id: str,
    runs_dir: str = Query(default="runs"),
) -> dict:
    run_dir = _resolve_run_dir(runs_dir, run_id)
    if not run_dir.exists():
        raise error_response(404, "RUN_NOT_FOUND", "Run not found")

    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "input_dir": str(run_dir / "input"),
        "artifacts_dir": str(run_dir / "artifacts"),
        "raw_dir": str(run_dir / "raw"),
        "trace_path": str(run_dir / "trace.json"),
        "result_path": str(run_dir / "result.json"),
        "has_trace": (run_dir / "trace.json").exists(),
        "has_result": (run_dir / "result.json").exists(),
    }


@router.get("/{run_id}/trace")
def get_run_trace(
    run_id: str,
    runs_dir: str = Query(default="runs"),
) -> dict:
    return _read_json(_resolve_run_dir(runs_dir, run_id) / "trace.json", "Trace not found")


@router.get("/{run_id}/result")
def get_run_result(
    run_id: str,
    runs_dir: str = Query(default="runs"),
) -> dict:
    return _read_json(_resolve_run_dir(runs_dir, run_id) / "result.json", "Result not found")


@router.get("/{run_id}/artifacts/{name:path}", response_class=FileResponse)
def get_run_artifact(
    run_id: str,
    name: str,
    runs_dir: str = Query(default="runs"),
) -> FileResponse:
    artifacts_dir = (_resolve_run_dir(runs_dir, run_id) / "artifacts").resolve()
    artifact_path = (artifacts_dir / name).resolve()
    if not _is_relative_to(artifact_path, artifacts_dir):
        raise error_response(400, "INVALID_ARTIFACT_PATH", "Invalid artifact path")
    if not artifact_path.exists() or not artifact_path.is_file():
        raise error_response(404, "ARTIFACT_NOT_FOUND", "Artifact not found")
    return FileResponse(artifact_path)


def _resolve_run_dir(runs_dir: str, run_id: str) -> Path:
    if "/" in run_id or "\\" in run_id or run_id in {"", ".", ".."}:
        raise error_response(400, "INVALID_RUN_ID", "Invalid run_id")
    return Path(runs_dir) / run_id


def _read_json(path: Path, not_found_message: str) -> dict:
    if not path.exists() or not path.is_file():
        raise error_response(404, "RUN_FILE_NOT_FOUND", not_found_message)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise error_response(500, "INVALID_RUN_JSON", f"Invalid JSON file: {path.name}") from exc
    if not isinstance(data, dict):
        raise error_response(500, "INVALID_RUN_JSON", f"Expected JSON object: {path.name}")
    return data


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
