from __future__ import annotations

from typing import Any

from ocr_engine_api.settings import get_api_settings


RUN_PATH_KEYS = {
    "run_dir",
    "input_dir",
    "artifacts_dir",
    "raw_dir",
    "trace_path",
    "result_path",
}
ARTIFACT_PATH_KEYS = {"path"}


def sanitize_for_public_response(payload: Any) -> Any:
    """Remove local filesystem paths from API responses in production."""
    if not get_api_settings().is_production:
        return payload
    return _sanitize(payload)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        run_id = value.get("run_id")
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if key in RUN_PATH_KEYS or key in ARTIFACT_PATH_KEYS:
                continue
            sanitized[key] = _sanitize(item)
        if isinstance(run_id, str) and run_id:
            sanitized.setdefault("links", run_links(run_id))
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def run_links(run_id: str) -> dict[str, str]:
    return {
        "run": f"/v1/runs/{run_id}",
        "result": f"/v1/runs/{run_id}/result",
        "trace": f"/v1/runs/{run_id}/trace",
        "artifacts": f"/v1/runs/{run_id}/artifacts",
    }
