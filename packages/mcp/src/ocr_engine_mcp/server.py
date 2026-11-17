from __future__ import annotations

import json
import os
from typing import Any

from fastmcp import FastMCP

from ocr_engine_mcp.auth import api_key_for_request, auth_from_env
from ocr_engine_mcp.client import OcrApiClient, OcrApiError
from ocr_engine_mcp import tools as mcp_tools


def create_mcp() -> FastMCP:
    mcp = FastMCP(name="FIBA OCR Engine", auth=auth_from_env())

    if path_input_allowed():
        # Reads a file path on the API host. Disabled in production (uploads/base64 only).
        @mcp.tool
        def submit_scoresheet_from_path(
            image_path: str,
            run_id: str | None = None,
            options: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            """Submit a scoresheet image path for async OCR processing and return a run id."""
            with _client() as client:
                return mcp_tools.submit_scoresheet_from_path(
                    client,
                    image_path,
                    run_id=run_id,
                    options=options,
                )

    @mcp.tool
    def submit_scoresheet_base64(
        image_base64: str,
        filename: str = "scoresheet.jpg",
        run_id: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upload a base64-encoded scoresheet image for async OCR processing and return a run id."""
        with _client() as client:
            return mcp_tools.submit_scoresheet_base64(
                client,
                image_base64,
                filename=filename,
                run_id=run_id,
                options=options,
            )

    @mcp.tool
    def poll_run(run_id: str) -> dict[str, Any]:
        """Poll one async OCR run and return its current status."""
        with _client() as client:
            return mcp_tools.poll_run(client, run_id)

    @mcp.tool
    def wait_for_run(
        run_id: str,
        timeout_seconds: float = 300,
        poll_interval_seconds: float = 2,
    ) -> dict[str, Any]:
        """Wait for an async OCR run to complete, fail, or time out."""
        with _client() as client:
            return mcp_tools.wait_for_run(
                client,
                run_id,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )

    @mcp.tool
    def list_runs(limit: int = 20) -> dict[str, Any]:
        """List recent OCR runs."""
        return _call_with_client(lambda client: client.list_runs(limit=limit))

    @mcp.tool
    def inspect_run(run_id: str) -> dict[str, Any]:
        """Inspect one OCR run and return summary plus MCP resource URIs."""
        with _client() as client:
            return mcp_tools.inspect_run(client, run_id)

    @mcp.tool
    def get_run_result(run_id: str) -> dict[str, Any]:
        """Return the structured OCR result for a run."""
        return _call_with_client(lambda client: client.get_run_result(run_id))

    @mcp.tool
    def get_run_trace(run_id: str) -> dict[str, Any]:
        """Return the audit trace for a run."""
        return _call_with_client(lambda client: client.get_run_trace(run_id))

    @mcp.tool
    def list_run_artifacts(run_id: str, limit: int = 200) -> dict[str, Any]:
        """List visual and JSON artifacts produced by a run."""
        return _call_with_client(lambda client: client.list_run_artifacts(run_id, limit=limit))

    @mcp.tool
    def get_artifact(run_id: str, artifact_name: str) -> dict[str, Any]:
        """Return one run artifact encoded as base64."""
        return _call_with_client(lambda client: client.get_artifact(run_id, artifact_name))

    @mcp.resource("run://{run_id}", mime_type="application/json")
    def run_resource(run_id: str) -> str:
        return _json_resource(_call_with_client(lambda client: client.get_run(run_id)))

    @mcp.resource("result://{run_id}", mime_type="application/json")
    def result_resource(run_id: str) -> str:
        return _json_resource(_call_with_client(lambda client: client.get_run_result(run_id)))

    @mcp.resource("trace://{run_id}", mime_type="application/json")
    def trace_resource(run_id: str) -> str:
        return _json_resource(_call_with_client(lambda client: client.get_run_trace(run_id)))

    @mcp.resource("artifact://{run_id}/{artifact_name}", mime_type="application/json")
    def artifact_resource(run_id: str, artifact_name: str) -> str:
        return _json_resource(_call_with_client(lambda client: client.get_artifact(run_id, artifact_name)))

    @mcp.prompt
    def review_extraction(run_id: str) -> str:
        """Prompt an agent to review OCR output using result and trace resources."""
        return (
            f"Review OCR run {run_id}. Read result://{run_id} and trace://{run_id}. "
            "Identify validation warnings, uncertain fields, missing sections, and artifacts "
            "that should be inspected before the result is accepted."
        )

    @mcp.prompt
    def suggest_retry_strategy(run_id: str) -> str:
        """Prompt an agent to suggest retry options for a run."""
        return (
            f"Inspect trace://{run_id} and result://{run_id}. Suggest whether the scoresheet "
            "should be retried, which step or section looks weakest, and which options or "
            "validation plugins could improve the next run."
        )

    @mcp.prompt
    def explain_validation_warnings(run_id: str) -> str:
        """Prompt an agent to explain validation warnings without inventing facts."""
        return (
            f"Read result://{run_id}. Explain each validation warning in practical terms. "
            "Do not decide business outcomes; only explain what the OCR engine reported and "
            "what a human reviewer should check."
        )

    return mcp


def path_input_allowed() -> bool:
    """Whether to expose `submit_scoresheet_from_path` (server-side file reads).

    MCP_ALLOW_PATH_INPUT overrides; otherwise enabled except when OCR_ENV=production.
    """
    value = os.getenv("MCP_ALLOW_PATH_INPUT", "").strip().lower()
    if value:
        return value in {"1", "true", "yes", "on"}
    return os.getenv("OCR_ENV", "development").strip().lower() != "production"


def _client() -> OcrApiClient:
    """Build an API client that forwards the caller's ocr_live_ key when present."""
    timeout = int(os.getenv("OCR_API_TIMEOUT_SECONDS", "300"))
    return OcrApiClient(api_key=api_key_for_request(), timeout_seconds=timeout)


def _call_with_client(callback: Any) -> dict[str, Any]:
    with _client() as client:
        try:
            return callback(client)
        except OcrApiError as exc:
            return mcp_tools.handle_api_error(exc)


def _json_resource(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


mcp = create_mcp()
app = mcp.http_app(transport="http")


def run() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT") or os.getenv("PORT") or "8001")
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    run()
