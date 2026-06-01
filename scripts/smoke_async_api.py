from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


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


def get_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, str] | None = None,
    timeout: float,
) -> dict[str, Any]:
    response = session.get(url, params=params, timeout=timeout)
    return parse_json_response(response)


def upload_image(
    session: requests.Session,
    url: str,
    *,
    image_path: Path,
    run_id: str,
    runs_dir: str,
    options_json: str | None,
    timeout: float,
) -> dict[str, Any]:
    data = {"run_id": run_id, "runs_dir": runs_dir}
    if options_json:
        try:
            json.loads(options_json)
        except json.JSONDecodeError as exc:
            raise SmokeFailure("--options-json must be valid JSON") from exc
        data["options_json"] = options_json

    with image_path.open("rb") as file_obj:
        files = {"file": (image_path.name, file_obj, guess_mime_type(image_path))}
        response = session.post(url, data=data, files=files, timeout=timeout)
    return parse_json_response(response)


def parse_json_response(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise SmokeFailure(f"Expected JSON response from {response.url}") from exc
    if response.status_code >= 400:
        raise SmokeFailure(f"HTTP {response.status_code} from {response.url}", payload)
    require(isinstance(payload, dict), f"Expected JSON object from {response.url}", payload)
    return payload


def cleanup_run(
    session: requests.Session,
    base_url: str,
    *,
    runs_dir: str,
    run_id: str,
    timeout: float,
) -> None:
    try:
        response = session.delete(
            f"{base_url}/v1/runs/{run_id}",
            params={"runs_dir": runs_dir},
            timeout=timeout,
        )
        if response.status_code in {200, 404}:
            print(f"cleanup: API returned HTTP {response.status_code} for {run_id}")
            return
        print(f"cleanup: API returned HTTP {response.status_code}; falling back to local delete", file=sys.stderr)
    except requests.RequestException as exc:
        print(f"cleanup: API request failed ({exc}); falling back to local delete", file=sys.stderr)

    run_dir = Path(runs_dir).expanduser() / run_id
    if not run_dir.is_absolute():
        run_dir = PROJECT_ROOT / run_dir
    if run_dir.exists():
        import shutil

        shutil.rmtree(run_dir)
        print(f"cleanup: removed {run_dir}")


def resolve_image(value: Path | None) -> Path:
    if value is not None:
        image_path = value.expanduser().resolve()
        require(image_path.exists(), f"Image not found: {image_path}")
        require(image_path.is_file(), f"Image path is not a file: {image_path}")
        require(image_path.suffix.lower() in IMAGE_SUFFIXES, f"Unsupported image extension: {image_path.suffix}")
        return image_path

    dataset_dir = PROJECT_ROOT / "dataset"
    candidates = sorted(
        path
        for suffix in IMAGE_SUFFIXES
        for path in dataset_dir.glob(f"sheet-*/*{suffix}")
        if path.is_file()
    )
    require(
        bool(candidates),
        "No dataset image found. Pass --image /path/to/sheet.jpg or place images under dataset/sheet-*.",
    )
    return candidates[0].resolve()


def guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"


def require(condition: bool, message: str, payload: Any | None = None) -> None:
    if not condition:
        raise SmokeFailure(message, payload)


class SmokeFailure(Exception):
    def __init__(self, message: str, payload: Any | None = None) -> None:
        super().__init__(message)
        self.payload = payload


if __name__ == "__main__":
    raise SystemExit(main())
