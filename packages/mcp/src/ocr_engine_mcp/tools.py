from __future__ import annotations

from typing import Any

from ocr_engine_mcp.client import OcrApiClient, OcrApiError


def handle_api_error(exc: OcrApiError) -> dict[str, Any]:
    return {
        "success": False,
        "error": exc.to_dict(),
        "next_actions": [
            "Check OCR_API_BASE_URL and OCR_API_KEY configuration.",
            "If the request processed a run, inspect the run trace when a run_id is available.",
        ],
    }


def process_submit_response(response: dict[str, Any]) -> dict[str, Any]:
    run_id = str(response.get("run_id") or "")
    status = response.get("status")
    return {
        "success": bool(response.get("success", True)),
        "run_id": run_id or None,
        "status": status,
        "summary": {
            "status": status,
            "links": response.get("links") if isinstance(response.get("links"), dict) else {},
        },
        "resources": _resources(run_id),
        "next_actions": _async_next_actions(run_id),
        "raw": response,
    }


def submit_scoresheet_from_path(
    client: OcrApiClient,
    image_path: str,
    *,
    run_id: str | None = None,
    runs_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return process_submit_response(
            client.submit_scoresheet_from_path(
                image_path,
                run_id=run_id,
                runs_dir=runs_dir,
                options=options,
            )
        )
    except OcrApiError as exc:
        return handle_api_error(exc)


def submit_scoresheet_base64(
    client: OcrApiClient,
    image_base64: str,
    *,
    filename: str = "scoresheet.jpg",
    run_id: str | None = None,
    runs_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return process_submit_response(
            client.submit_scoresheet_base64(
                image_base64,
                filename=filename,
                run_id=run_id,
                runs_dir=runs_dir,
                options=options,
            )
        )
    except OcrApiError as exc:
        return handle_api_error(exc)


def poll_run(client: OcrApiClient, run_id: str, *, runs_dir: str | None = None) -> dict[str, Any]:
    try:
        run = client.poll_run(run_id, runs_dir=runs_dir)
        return _run_status_response(run_id, run)
    except OcrApiError as exc:
        return handle_api_error(exc)


def wait_for_run(
    client: OcrApiClient,
    run_id: str,
    *,
    timeout_seconds: float = 300,
    poll_interval_seconds: float = 2,
    runs_dir: str | None = None,
) -> dict[str, Any]:
    try:
        run = client.wait_for_run(
            run_id,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            runs_dir=runs_dir,
        )
        return _run_status_response(run_id, run)
    except OcrApiError as exc:
        if exc.code == "RUN_TIMEOUT":
            last_run = exc.details.get("run") if isinstance(exc.details, dict) else None
            return {
                "success": False,
                "run_id": run_id,
                "status": last_run.get("status") if isinstance(last_run, dict) else "unknown",
                "error": {
                    "code": "RUN_TIMEOUT",
                    "message": exc.message,
                },
                "run": last_run,
                "resources": _resources(run_id),
                "next_actions": ["Poll the run again later.", "Increase timeout_seconds if this run is expected to be slow."],
            }
        if isinstance(exc.details, dict) and exc.details.get("terminal_status") == "failed":
            run = exc.details["run"]
            return {
                "success": False,
                "run_id": run_id,
                "status": run.get("status", "failed"),
                "run": run,
                "resources": _resources(run_id),
                "next_actions": ["Inspect the run trace.", "Review the error and retry with adjusted options."],
            }
        return handle_api_error(exc)


def inspect_run(client: OcrApiClient, run_id: str, *, runs_dir: str | None = None) -> dict[str, Any]:
    try:
        run = client.get_run(run_id, runs_dir=runs_dir)
        return {
            "success": True,
            "run_id": run_id,
            "run": run,
            "resources": _resources(run_id),
            "next_actions": ["Read result or trace if the run needs review."],
        }
    except OcrApiError as exc:
        return handle_api_error(exc)


def _run_status_response(run_id: str, run: dict[str, Any]) -> dict[str, Any]:
    status = run.get("status")
    next_actions = ["Poll again until completed.", "Read result when completed."]
    if status == "completed":
        next_actions = ["Read result.json.", "Read trace.json if review is needed."]
    return {
        "success": True,
        "run_id": run_id,
        "status": status,
        "run": run,
        "resources": _resources(run_id),
        "next_actions": next_actions,
    }


def _resources(run_id: str) -> dict[str, str]:
    if not run_id:
        return {}
    return {
        "run": f"run://{run_id}",
        "result": f"result://{run_id}",
        "trace": f"trace://{run_id}",
    }


def _async_next_actions(run_id: str) -> list[str]:
    if not run_id:
        return []
    return [
        "Poll run status with poll_run.",
        "Use wait_for_run if you want the MCP tool to wait until completion.",
        "Read result.json after the run is completed.",
    ]
