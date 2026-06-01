from __future__ import annotations

from typing import Any

from ocr_engine_mcp.client import OcrApiClient, OcrApiError


def process_api_response(response: dict[str, Any]) -> dict[str, Any]:
    run_id = str(response.get("run_id") or response.get("data", {}).get("context", {}).get("run_id") or "")
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    warnings = response.get("warnings")
    if warnings is None and isinstance(result, dict):
        warnings = result.get("validation_warnings", [])
    return {
        "success": bool(response.get("success", True)),
        "run_id": run_id or None,
        "status": response.get("status") or result.get("match_status"),
        "summary": {
            "match_status": result.get("match_status"),
            "result_path": data.get("result_path"),
            "trace_path": data.get("trace_path"),
            "artifacts_dir": data.get("artifacts_dir"),
            "total_tokens": result.get("meta", {}).get("total_tokens") if isinstance(result.get("meta"), dict) else None,
        },
        "warnings": warnings or [],
        "resources": _resources(run_id),
        "next_actions": _next_actions(run_id, warnings or []),
        "raw": response,
    }


def handle_api_error(exc: OcrApiError) -> dict[str, Any]:
    return {
        "success": False,
        "error": exc.to_dict(),
        "next_actions": [
            "Check OCR_API_BASE_URL and OCR_API_KEY configuration.",
            "If the request processed a run, inspect the run trace when a run_id is available.",
        ],
    }


def process_scoresheet_from_path(
    client: OcrApiClient,
    image_path: str,
    *,
    run_id: str | None = None,
    runs_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return process_api_response(
            client.run_full_pipeline(
                image_path,
                run_id=run_id,
                runs_dir=runs_dir,
                options=options,
            )
        )
    except OcrApiError as exc:
        return handle_api_error(exc)


def process_scoresheet_base64(
    client: OcrApiClient,
    image_base64: str,
    *,
    filename: str = "scoresheet.jpg",
    run_id: str | None = None,
    runs_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return process_api_response(
            client.upload_scoresheet_base64(
                image_base64,
                filename=filename,
                run_id=run_id,
                runs_dir=runs_dir,
                options=options,
            )
        )
    except OcrApiError as exc:
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


def _resources(run_id: str) -> dict[str, str]:
    if not run_id:
        return {}
    return {
        "run": f"run://{run_id}",
        "result": f"result://{run_id}",
        "trace": f"trace://{run_id}",
    }


def _next_actions(run_id: str, warnings: list[Any]) -> list[str]:
    if not run_id:
        return []
    actions = ["Inspect run details.", "Read result.json.", "Read trace.json."]
    if warnings:
        actions.append("Review validation warnings before trusting the extraction.")
    return actions
