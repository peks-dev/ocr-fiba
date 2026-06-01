from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from smoke_api import (
    SmokeFailure,
    cleanup_run,
    get_json,
    parse_json_response,
    require,
    resolve_image,
    upload_image,
)


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    image_path = resolve_image(args.image)
    run_id = args.run_id or make_run_id()

    print(f"base_url: {base_url}")
    print(f"image: {image_path}")
    print(f"run_id: {run_id}")
    print(f"runs_dir: {args.runs_dir}")

    session = requests.Session()
    try:
        health = get_json(session, f"{base_url}/health", timeout=args.timeout)
        require(isinstance(health, dict), "Health response must be a JSON object")

        submitted = upload_image(
            session,
            f"{base_url}/v1/runs/upload",
            image_path=image_path,
            run_id=run_id,
            runs_dir=args.runs_dir,
            options_json=args.options_json,
            timeout=args.timeout,
        )
        require(submitted.get("success") is True, "Submit response success must be true", submitted)
        require(submitted.get("run_id") == run_id, "Submit response run_id must match request", submitted)
        require(submitted.get("status") == "queued", "Submit response status must be queued", submitted)

        detail = wait_for_run(
            session,
            base_url,
            run_id=run_id,
            runs_dir=args.runs_dir,
            timeout=args.wait_timeout,
            interval=args.poll_interval,
            request_timeout=args.timeout,
        )
        require(detail.get("status") == "completed", "Run must complete", detail)
        require(detail.get("has_result") is True, "Completed run must report result.json", detail)
        require(detail.get("has_trace") is True, "Completed run must report trace.json", detail)

        result = get_json(
            session,
            f"{base_url}/v1/runs/{run_id}/result",
            params={"runs_dir": args.runs_dir},
            timeout=args.timeout,
        )
        require(isinstance(result, dict), "Result endpoint must return a JSON object")

        print("async smoke test passed")
        return 0
    except SmokeFailure as exc:
        print(f"async smoke test failed: {exc}", file=sys.stderr)
        if exc.payload is not None:
            print(json.dumps(exc.payload, indent=2, ensure_ascii=False, default=str), file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"async smoke test failed: HTTP request error: {exc}", file=sys.stderr)
        return 1
    finally:
        if args.cleanup:
            cleanup_run(session, base_url, runs_dir=args.runs_dir, run_id=run_id, timeout=args.timeout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test for the async local OCR runs API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--image", type=Path, help="Path to a sheet image. Defaults to first dataset image found.")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--run-id", help="Run id to use. Defaults to smoke_async_<timestamp>.")
    parser.add_argument("--options-json", help="Pipeline options as a JSON string.")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--wait-timeout", type=float, default=600.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--cleanup", action="store_true", help="Remove the generated run directory after the smoke test.")
    return parser.parse_args()


def make_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"smoke_async_{timestamp}"


def wait_for_run(
    session: requests.Session,
    base_url: str,
    *,
    run_id: str,
    runs_dir: str,
    timeout: float,
    interval: float,
    request_timeout: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_detail: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        response = session.get(
            f"{base_url}/v1/runs/{run_id}",
            params={"runs_dir": runs_dir},
            timeout=request_timeout,
        )
        detail = parse_json_response(response)
        last_detail = detail
        status = detail.get("status")
        print(f"poll: status={status} progress={detail.get('progress')}")
        if status == "completed":
            return detail
        if status == "failed":
            raise SmokeFailure("Run failed", detail)
        time.sleep(interval)
    raise SmokeFailure(f"Run did not complete within {timeout} seconds", last_detail)


if __name__ == "__main__":
    raise SystemExit(main())
