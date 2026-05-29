from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from api.errors import error_response

router = APIRouter(prefix="/v1/runs", tags=["runs"])


@router.get("")
def list_runs(
    runs_dir: Annotated[str, Query()] = "runs",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict:
    base_dir = Path(runs_dir)
    if not base_dir.exists():
        return {"runs_dir": str(base_dir), "count": 0, "runs": []}
    if not base_dir.is_dir():
        raise error_response(400, "INVALID_RUNS_DIR", "runs_dir is not a directory")

    run_dirs = [path for path in base_dir.iterdir() if path.is_dir()]
    run_dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    runs = [_run_summary(path) for path in run_dirs[:limit]]
    return {
        "runs_dir": str(base_dir),
        "count": len(runs),
        "runs": runs,
    }


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


@router.get("/{run_id}/artifacts")
def list_run_artifacts(
    run_id: str,
    runs_dir: Annotated[str, Query()] = "runs",
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> dict:
    run_dir = _resolve_run_dir(runs_dir, run_id)
    if not run_dir.exists():
        raise error_response(404, "RUN_NOT_FOUND", "Run not found")

    artifacts_dir = (run_dir / "artifacts").resolve()
    if not artifacts_dir.exists():
        return {
            "run_id": run_id,
            "artifacts_dir": str(artifacts_dir),
            "count": 0,
            "artifacts": [],
        }
    if not artifacts_dir.is_dir():
        raise error_response(500, "INVALID_ARTIFACTS_DIR", "artifacts is not a directory")

    artifacts = _list_artifact_files(artifacts_dir, limit)
    return {
        "run_id": run_id,
        "artifacts_dir": str(artifacts_dir),
        "count": len(artifacts),
        "artifacts": artifacts,
    }


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


def _run_summary(run_dir: Path) -> dict:
    result_path = run_dir / "result.json"
    trace_path = run_dir / "trace.json"
    input_dir = run_dir / "input"
    result = _read_optional_json(result_path)
    return {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "input_dir": str(input_dir),
        "artifacts_dir": str(run_dir / "artifacts"),
        "raw_dir": str(run_dir / "raw"),
        "trace_path": str(trace_path),
        "result_path": str(result_path),
        "has_trace": trace_path.exists(),
        "has_result": result_path.exists(),
        "match_status": result.get("match_status") if result else None,
        "input_files": _list_input_files(input_dir),
        "modified_at": run_dir.stat().st_mtime,
    }


def _read_optional_json(path: Path) -> dict | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _list_input_files(input_dir: Path) -> list[str]:
    if not input_dir.exists() or not input_dir.is_dir():
        return []
    return sorted(path.name for path in input_dir.iterdir() if path.is_file())


def _list_artifact_files(artifacts_dir: Path, limit: int) -> list[dict]:
    artifacts = []
    for path in sorted(artifacts_dir.rglob("*")):
        if len(artifacts) >= limit:
            break
        if not path.is_file():
            continue
        resolved_path = path.resolve()
        if not _is_relative_to(resolved_path, artifacts_dir):
            continue
        relative_name = resolved_path.relative_to(artifacts_dir).as_posix()
        artifacts.append(
            {
                "name": relative_name,
                "path": str(resolved_path),
                "size_bytes": resolved_path.stat().st_size,
                "modified_at": resolved_path.stat().st_mtime,
            }
        )
    return artifacts


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
