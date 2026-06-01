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
    run_id = args.run_id or f"mcp_async_smoke_{time.strftime('%Y%m%d_%H%M%S')}"

    asyncio.run(
        run_smoke(
            mcp_url=args.mcp_url,
            api_url=args.api_url,
            api_key=args.api_key,
            image_path=image_path,
            run_id=run_id,
            wait_timeout=args.wait_timeout,
            poll_interval=args.poll_interval,
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
    wait_timeout: float,
    poll_interval: float,
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
            "submit_scoresheet_base64",
            "poll_run",
            "wait_for_run",
            "get_run_result",
        }
        missing_tools = sorted(required_tools - tool_names)
        if missing_tools:
            raise AssertionError(f"Missing MCP tools: {missing_tools}")

        submit = await _call_tool_data(
            client,
            "submit_scoresheet_base64",
            {
                "image_base64": image_base64,
                "filename": image_path.name,
                "run_id": run_id,
            },
        )
        _assert_success(submit, "submit_scoresheet_base64")
        if submit.get("run_id") != run_id:
            raise AssertionError(f"Expected run_id {run_id}, got {submit.get('run_id')}")
        if submit.get("status") != "queued":
            raise AssertionError(f"Expected queued submit status, got {submit.get('status')}")

        poll = await _call_tool_data(client, "poll_run", {"run_id": run_id})
        _assert_success(poll, "poll_run")
        print(f"initial status: {poll.get('status')}")

        waited = await _call_tool_data(
            client,
            "wait_for_run",
            {
                "run_id": run_id,
                "timeout_seconds": wait_timeout,
                "poll_interval_seconds": poll_interval,
            },
        )
        _assert_success(waited, "wait_for_run")
        if waited.get("status") != "completed":
            raise AssertionError(f"Expected completed run, got {waited.get('status')}")

        result = await _call_tool_data(client, "get_run_result", {"run_id": run_id})
        if not isinstance(result, dict) or "match_status" not in result:
            raise AssertionError("get_run_result did not return a result with match_status")

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

    print("async MCP smoke test passed")


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
    parser = argparse.ArgumentParser(description="Smoke test the async FIBA OCR MCP tools.")
    parser.add_argument("--mcp-url", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default=os.getenv("OCR_API_KEY"))
    parser.add_argument("--image", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--wait-timeout", type=float, default=600)
    parser.add_argument("--poll-interval", type=float, default=2)
    parser.add_argument("--cleanup", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
