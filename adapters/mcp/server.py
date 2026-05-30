from __future__ import annotations

import json
import os
from typing import Any

from fastmcp import FastMCP

from adapters.mcp.client import OcrApiClient, OcrApiError
from adapters.mcp import tools as mcp_tools


def create_mcp() -> FastMCP:
    mcp = FastMCP(name="FIBA OCR Engine")

    @mcp.tool
    def process_scoresheet_from_path(
        image_path: str,
        run_id: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a scoresheet image path that is accessible to the OCR API service."""
        return mcp_tools.process_scoresheet_from_path(
            _client(),
            image_path,
            run_id=run_id,
            options=options,
        )

    @mcp.tool
    def process_scoresheet_base64(
        image_base64: str,
        filename: str = "scoresheet.jpg",
        run_id: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upload a base64-encoded scoresheet image and process it with the OCR API."""
        return mcp_tools.process_scoresheet_base64(
            _client(),
            image_base64,
            filename=filename,
            run_id=run_id,
            options=options,
        )

    @mcp.tool
    def list_runs(limit: int = 20) -> dict[str, Any]:
        """List recent OCR runs."""
        try:
            return _client().list_runs(limit=limit)
        except OcrApiError as exc:
            return mcp_tools.handle_api_error(exc)

    @mcp.tool
    def inspect_run(run_id: str) -> dict[str, Any]:
        """Inspect one OCR run and return summary plus MCP resource URIs."""
        return mcp_tools.inspect_run(_client(), run_id)

    @mcp.tool
    def get_run_result(run_id: str) -> dict[str, Any]:
        """Return the structured OCR result for a run."""
        try:
            return _client().get_run_result(run_id)
        except OcrApiError as exc:
            return mcp_tools.handle_api_error(exc)

    @mcp.tool
    def get_run_trace(run_id: str) -> dict[str, Any]:
        """Return the audit trace for a run."""
        try:
            return _client().get_run_trace(run_id)
        except OcrApiError as exc:
            return mcp_tools.handle_api_error(exc)

    @mcp.tool
    def list_run_artifacts(run_id: str, limit: int = 200) -> dict[str, Any]:
        """List visual and JSON artifacts produced by a run."""
        try:
            return _client().list_run_artifacts(run_id, limit=limit)
        except OcrApiError as exc:
            return mcp_tools.handle_api_error(exc)

    @mcp.tool
    def get_artifact(run_id: str, artifact_name: str) -> dict[str, Any]:
        """Return one run artifact encoded as base64."""
        try:
            return _client().get_artifact(run_id, artifact_name)
        except OcrApiError as exc:
            return mcp_tools.handle_api_error(exc)

    @mcp.resource("run://{run_id}", mime_type="application/json")
    def run_resource(run_id: str) -> str:
        return _json_resource(_client().get_run(run_id))

    @mcp.resource("result://{run_id}", mime_type="application/json")
    def result_resource(run_id: str) -> str:
        return _json_resource(_client().get_run_result(run_id))

    @mcp.resource("trace://{run_id}", mime_type="application/json")
    def trace_resource(run_id: str) -> str:
        return _json_resource(_client().get_run_trace(run_id))

    @mcp.resource("artifact://{run_id}/{artifact_name}", mime_type="application/json")
    def artifact_resource(run_id: str, artifact_name: str) -> str:
        return _json_resource(_client().get_artifact(run_id, artifact_name))

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


def _client() -> OcrApiClient:
    timeout = int(os.getenv("OCR_API_TIMEOUT_SECONDS", "300"))
    return OcrApiClient(timeout_seconds=timeout)


def _json_resource(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


mcp = create_mcp()
app = mcp.http_app(transport="http")


def run() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8001"))
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    run()
