from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from ocr_engine_api.responses import run_links
from ocr_engine_api.settings import get_api_settings

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


RUN_STATUS_QUEUED = "queued"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELLED = "cancelled"
ACTIVE_RUN_STATUSES = {RUN_STATUS_QUEUED, RUN_STATUS_RUNNING}
FAILED_RUN_STATUSES = {RUN_STATUS_FAILED}
VALID_RUN_STATUSES = {
    RUN_STATUS_QUEUED,
    RUN_STATUS_RUNNING,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_CANCELLED,
}


@dataclass(frozen=True)
class RunRepositoryError(Exception):
    status_code: int
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


class RunRepository:
    """Filesystem-backed access to OCR run records."""

    def __init__(
        self,
        runs_dir: str | Path = "runs",
        *,
        stale_run_seconds: float | None = None,
    ) -> None:
        self.runs_dir = Path(runs_dir)
        self.stale_run_seconds = (
            float(stale_run_seconds)
            if stale_run_seconds is not None
            else float(get_api_settings().stale_run_seconds)
        )

    def list_runs(self, *, limit: int = 50) -> dict:
        if not self.runs_dir.exists():
            return {"runs_dir": str(self.runs_dir), "count": 0, "runs": []}
        if not self.runs_dir.is_dir():
            raise RunRepositoryError(400, "INVALID_RUNS_DIR", "runs_dir is not a directory")

        run_dirs = [
            path
            for path in self.runs_dir.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        ]
        run_dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        runs = [self._run_summary(path) for path in run_dirs[:limit]]
        return {
            "runs_dir": str(self.runs_dir),
            "count": len(runs),
            "runs": runs,
        }

    def ensure_new_run_available(self, run_id: str) -> Path:
        """Validate run_id syntax and ensure no run directory already exists for it."""
        run_dir = self.resolve_run_dir(run_id)
        if run_dir.exists():
            raise RunRepositoryError(409, "RUN_ALREADY_EXISTS", f"Run '{run_id}' already exists")
        return run_dir

    def reserve_run_dir(self, run_id: str) -> Path:
        """Atomically create a new run directory, failing with 409 on collision."""
        run_dir = self.resolve_run_dir(run_id)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        try:
            run_dir.mkdir(parents=False, exist_ok=False)
        except FileExistsError as exc:
            raise RunRepositoryError(409, "RUN_ALREADY_EXISTS", f"Run '{run_id}' already exists") from exc
        return run_dir

    def get_run(self, run_id: str) -> dict:
        run_dir = self.resolve_run_dir(run_id)
        if not run_dir.exists():
            raise RunRepositoryError(404, "RUN_NOT_FOUND", "Run not found")

        detail = self._run_summary(run_dir)
        artifacts_dir = (run_dir / "artifacts").resolve()
        artifacts = self._list_artifact_files(artifacts_dir, limit=500) if artifacts_dir.is_dir() else []
        detail["artifacts_count"] = len(artifacts)
        detail["artifacts"] = artifacts[:20]
        return detail

    def create_status(
        self,
        run_id: str,
        *,
        status: str = RUN_STATUS_QUEUED,
        exist_ok: bool = False,
    ) -> dict:
        if status not in VALID_RUN_STATUSES:
            raise RunRepositoryError(400, "INVALID_RUN_STATUS", "Invalid run status")
        now = time.time()
        if exist_ok:
            run_dir = self.resolve_run_dir(run_id)
            run_dir.mkdir(parents=True, exist_ok=True)
        else:
            run_dir = self.reserve_run_dir(run_id)
        status_payload = {
            "run_id": run_id,
            "status": status,
            "created_at": now,
            "started_at": now if status == RUN_STATUS_RUNNING else None,
            "completed_at": now if status in {RUN_STATUS_COMPLETED, RUN_STATUS_FAILED} else None,
            "updated_at": now,
            "progress": None,
            "error": None,
            "links": run_links(run_id),
        }
        self._write_status(run_id, status_payload)
        return status_payload

    def update_status(
        self,
        run_id: str,
        *,
        status: str | None = None,
        progress: dict | None = None,
        error: dict | None = None,
    ) -> dict:
        if status is not None and status not in VALID_RUN_STATUSES:
            raise RunRepositoryError(400, "INVALID_RUN_STATUS", "Invalid run status")

        current = self.get_status(run_id)
        now = time.time()
        next_status = status or current.get("status") or RUN_STATUS_QUEUED
        current["status"] = next_status
        current["updated_at"] = now
        current["links"] = run_links(run_id)

        if progress is not None:
            current["progress"] = progress
        if error is not None:
            current["error"] = error
        elif next_status != RUN_STATUS_FAILED:
            current["error"] = None

        if next_status == RUN_STATUS_RUNNING and current.get("started_at") is None:
            current["started_at"] = now
        if next_status in {RUN_STATUS_COMPLETED, RUN_STATUS_FAILED, RUN_STATUS_CANCELLED}:
            current["completed_at"] = current.get("completed_at") or now

        self._write_status(run_id, current)
        return current

    def get_status(self, run_id: str) -> dict:
        run_dir = self.resolve_run_dir(run_id)
        if not run_dir.exists():
            raise RunRepositoryError(404, "RUN_NOT_FOUND", "Run not found")
        status = _read_optional_json(run_dir / "status.json")
        if status is None:
            return {
                "run_id": run_id,
                "status": RUN_STATUS_COMPLETED if (run_dir / "result.json").exists() else None,
                "created_at": None,
                "started_at": None,
                "completed_at": None,
                "updated_at": run_dir.stat().st_mtime,
                "progress": None,
                "error": None,
                "links": run_links(run_id),
            }
        status.setdefault("run_id", run_id)
        status.setdefault("links", run_links(run_id))
        return self._reconcile_active_status(run_dir, status)

    def _reconcile_active_status(self, run_dir: Path, status: dict) -> dict:
        """Reconcile orphaned queued/running statuses when a worker crashed or timed out."""
        if status.get("status") not in ACTIVE_RUN_STATUSES:
            return status

        updated_at = status.get("updated_at")
        if not isinstance(updated_at, (int, float)):
            updated_at = run_dir.stat().st_mtime
        age = time.time() - float(updated_at)

        result_path = run_dir / "result.json"
        if result_path.exists() and age > 5.0 and _read_optional_json(result_path) is not None:
            reconciled = {
                **status,
                "status": RUN_STATUS_COMPLETED,
                "completed_at": status.get("completed_at") or result_path.stat().st_mtime,
                "error": None,
            }
            return reconciled

        if self.stale_run_seconds > 0 and age > self.stale_run_seconds:
            return {
                **status,
                "status": RUN_STATUS_FAILED,
                "completed_at": status.get("completed_at") or time.time(),
                "error": {
                    "code": "RUN_STALLED",
                    "message": "OCR run stalled or worker restarted before completion",
                    "retryable": True,
                },
            }
        return status

    def delete_run(self, run_id: str) -> dict:
        run_dir = self.resolve_run_dir(run_id)
        if not run_dir.exists():
            raise RunRepositoryError(404, "RUN_NOT_FOUND", "Run not found")
        if not run_dir.is_dir():
            raise RunRepositoryError(400, "INVALID_RUN_DIR", "Run path is not a directory")

        shutil.rmtree(run_dir)
        return {
            "success": True,
            "run_id": run_id,
            "deleted": True,
        }

    def get_trace(self, run_id: str) -> dict:
        return self._read_json(self.resolve_run_dir(run_id) / "trace.json", "Trace not found")

    def get_result(self, run_id: str) -> dict:
        status = self.get_status(run_id)
        if status.get("status") in ACTIVE_RUN_STATUSES:
            raise RunRepositoryError(409, "RUN_NOT_COMPLETED", "Run is not completed yet")
        if status.get("status") in FAILED_RUN_STATUSES:
            raise RunRepositoryError(422, "RUN_FAILED", "Run failed")
        return self._read_json(self.resolve_run_dir(run_id) / "result.json", "Result not found")

    def list_artifacts(self, run_id: str, *, limit: int = 200) -> dict:
        run_dir = self.resolve_run_dir(run_id)
        if not run_dir.exists():
            raise RunRepositoryError(404, "RUN_NOT_FOUND", "Run not found")

        artifacts_dir = (run_dir / "artifacts").resolve()
        if not artifacts_dir.exists():
            return {
                "run_id": run_id,
                "artifacts_dir": str(artifacts_dir),
                "count": 0,
                "artifacts": [],
            }
        if not artifacts_dir.is_dir():
            raise RunRepositoryError(500, "INVALID_ARTIFACTS_DIR", "artifacts is not a directory")

        artifacts = self._list_artifact_files(artifacts_dir, limit)
        return {
            "run_id": run_id,
            "artifacts_dir": str(artifacts_dir),
            "count": len(artifacts),
            "artifacts": artifacts,
        }

    def resolve_artifact(self, run_id: str, name: str) -> Path:
        artifacts_dir = (self.resolve_run_dir(run_id) / "artifacts").resolve()
        artifact_path = (artifacts_dir / name).resolve()
        if not _is_relative_to(artifact_path, artifacts_dir):
            raise RunRepositoryError(400, "INVALID_ARTIFACT_PATH", "Invalid artifact path")
        if not artifact_path.exists() or not artifact_path.is_file():
            raise RunRepositoryError(404, "ARTIFACT_NOT_FOUND", "Artifact not found")
        return artifact_path

    def resolve_run_dir(self, run_id: str) -> Path:
        if not RUN_ID_RE.fullmatch(run_id) or ".." in run_id:
            raise RunRepositoryError(400, "INVALID_RUN_ID", "Invalid run_id")
        return self.runs_dir / run_id

    def _read_json(self, path: Path, not_found_message: str) -> dict:
        if not path.exists() or not path.is_file():
            raise RunRepositoryError(404, "RUN_FILE_NOT_FOUND", not_found_message)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RunRepositoryError(500, "INVALID_RUN_JSON", f"Invalid JSON file: {path.name}") from exc
        if not isinstance(data, dict):
            raise RunRepositoryError(500, "INVALID_RUN_JSON", f"Expected JSON object: {path.name}")
        return data

    def _write_status(self, run_id: str, status: dict) -> None:
        status_path = self.resolve_run_dir(run_id) / "status.json"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(status, indent=2, ensure_ascii=False) + "\n"
        tmp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=status_path.parent,
                prefix=".status-",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                tmp_name = tmp_file.name
                tmp_file.write(payload)
            os.replace(tmp_name, status_path)
            tmp_name = None
        finally:
            if tmp_name is not None:
                Path(tmp_name).unlink(missing_ok=True)

    def _run_summary(self, run_dir: Path) -> dict:
        result_path = run_dir / "result.json"
        trace_path = run_dir / "trace.json"
        input_dir = run_dir / "input"
        result = _read_optional_json(result_path)
        status = _read_optional_json(run_dir / "status.json") or {}
        if status:
            status = self._reconcile_active_status(run_dir, status)
        run_status = status.get("status")
        if run_status is None and result_path.exists():
            run_status = RUN_STATUS_COMPLETED
        return {
            "run_id": run_dir.name,
            "status": run_status,
            "progress": status.get("progress"),
            "error": status.get("error"),
            "links": status.get("links") or run_links(run_dir.name),
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

    def _list_artifact_files(self, artifacts_dir: Path, limit: int) -> list[dict]:
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


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
