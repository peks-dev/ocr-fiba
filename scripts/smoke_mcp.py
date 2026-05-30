from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from fastmcp import Client


def main() -> None:
    args = parse_args()
    image_path = _resolve_image(args.image)
    run_id = args.run_id or f"mcp_smoke_{time.strftime('%Y%m%d_%H%M%S')}"

    asyncio.run(
        run_smoke(
            mcp_url=args.mcp_url,
            api_url=args.api_url,
            api_key=args.api_key,
            image_path=image_path,
            run_id=run_id,
            cleanup=args.cleanup,
        )
    )


async def run_smoke(
    *,
    mcp_url: str,
    api_url: str,
    api_key: str | None,
    image_path: Path,
    run_id: str,
    cleanup: bool,
) -> None:
    print(f"mcp_url: {mcp_url}")
    print(f"api_url: {api_url}")
    print(f"image: {image_path}")
    print(f"run_id: {run_id}")

    image_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")

    async with Client(mcp_url) as client:
        await client.ping()
        tools = await client.list_tools()
        tool_names = {tool.name for tool in tools}
        required_tools = {
            "process_scoresheet_base64",
            "inspect_run",
            "get_run_result",
            "get_run_trace",
            "list_run_artifacts",
        }
        missing_tools = sorted(required_tools - tool_names)
        if missing_tools:
            raise AssertionError(f"Missing MCP tools: {missing_tools}")

        process = await _call_tool_data(
            client,
            "process_scoresheet_base64",
            {
                "image_base64": image_base64,
                "filename": image_path.name,
                "run_id": run_id,
            },
        )
        _assert_success(process, "process_scoresheet_base64")
        if process.get("run_id") != run_id:
            raise AssertionError(f"Expected run_id {run_id}, got {process.get('run_id')}")

        inspect = await _call_tool_data(client, "inspect_run", {"run_id": run_id})
        _assert_success(inspect, "inspect_run")
        if inspect.get("run", {}).get("run_id") != run_id:
            raise AssertionError("inspect_run did not return the expected run")

        result = await _call_tool_data(client, "get_run_result", {"run_id": run_id})
        if not isinstance(result, dict) or "match_status" not in result:
            raise AssertionError("get_run_result did not return a result with match_status")

        trace = await _call_tool_data(client, "get_run_trace", {"run_id": run_id})
        if not isinstance(trace, dict) or trace.get("run_id") != run_id:
            raise AssertionError("get_run_trace did not return the expected run trace")
        if "steps" not in trace:
            raise AssertionError("get_run_trace response is missing steps")

        artifacts = await _call_tool_data(client, "list_run_artifacts", {"run_id": run_id})
        if not isinstance(artifacts, dict) or "artifacts" not in artifacts:
            raise AssertionError("list_run_artifacts did not return artifacts")

    if cleanup:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
        response = requests.delete(
            f"{api_url.rstrip('/')}/v1/runs/{run_id}",
            headers=headers,
            timeout=30,
        )
        if response.status_code != 200:
            raise AssertionError(f"cleanup failed: HTTP {response.status_code} {response.text}")
        print("cleanup: API returned HTTP 200")

    print("mcp smoke test passed")


async def _call_tool_data(client: Client, name: str, arguments: dict[str, Any]) -> Any:
    result = await client.call_tool(name, arguments)
    if hasattr(result, "data"):
        return result.data
    if isinstance(result, list) and result and hasattr(result[0], "text"):
        return json.loads(result[0].text)
    return result


def _assert_success(payload: Any, tool_name: str) -> None:
    if not isinstance(payload, dict):
        raise AssertionError(f"{tool_name} returned non-dict payload: {payload!r}")
    if not payload.get("success"):
        raise AssertionError(f"{tool_name} failed: {json.dumps(payload, indent=2)}")


def _resolve_image(value: str | None) -> Path:
    if value:
        path = Path(value)
        if not path.exists() or not path.is_file():
            raise SystemExit(f"image not found: {path}")
        return path

    candidates = sorted(Path("dataset").glob("sheet-*/*"))
    for candidate in candidates:
        if candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            return candidate
    raise SystemExit("No dataset image found. Pass --image /path/to/scoresheet.jpg")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test the FIBA OCR MCP server.")
    parser.add_argument("--mcp-url", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default=os.getenv("OCR_API_KEY"))
    parser.add_argument("--image", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--cleanup", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
