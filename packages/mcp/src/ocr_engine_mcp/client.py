from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


DEFAULT_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class OcrApiError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status_code": self.status_code,
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class OcrApiClient:
    """HTTP client used by the remote MCP adapter."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        api_key: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("OCR_API_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("OCR_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def submit_scoresheet_from_path(
        self,
        image_path: str,
        *,
        run_id: str | None = None,
        runs_dir: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "image_path": image_path,
        }
        if run_id:
            payload["run_id"] = run_id
        if runs_dir:
            payload["runs_dir"] = runs_dir
        if options:
            payload["options"] = options
        response = self.session.post(
            self._url("/v1/runs"),
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        return self._json_response(response)

    def submit_scoresheet(
        self,
        image_bytes: bytes,
        *,
        filename: str = "scoresheet.jpg",
        run_id: str | None = None,
        runs_dir: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data: dict[str, str] = {}
        if run_id:
            data["run_id"] = run_id
        if runs_dir:
            data["runs_dir"] = runs_dir
        if options:
            data["options_json"] = json.dumps(options)
        files = {
            "file": (Path(filename).name or "scoresheet.jpg", image_bytes),
        }
        response = self.session.post(
            self._url("/v1/runs/upload"),
            data=data,
            files=files,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        return self._json_response(response)

    def submit_scoresheet_base64(
        self,
        image_base64: str,
        *,
        filename: str = "scoresheet.jpg",
        run_id: str | None = None,
        runs_dir: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            image_bytes = base64.b64decode(image_base64, validate=True)
        except ValueError as exc:
            raise OcrApiError(400, "INVALID_IMAGE_BASE64", "image_base64 must be valid base64") from exc
        if not image_bytes:
            raise OcrApiError(400, "EMPTY_IMAGE", "image_base64 decoded to empty bytes")
        return self.submit_scoresheet(
            image_bytes,
            filename=filename,
            run_id=run_id,
            runs_dir=runs_dir,
            options=options,
        )

    def list_runs(self, *, limit: int = 50, runs_dir: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if runs_dir:
            params["runs_dir"] = runs_dir
        response = self.session.get(
            self._url("/v1/runs"),
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        return self._json_response(response)

    def get_run(self, run_id: str, *, runs_dir: str | None = None) -> dict[str, Any]:
        return self._get_run_json(f"/v1/runs/{run_id}", runs_dir=runs_dir)

    def poll_run(self, run_id: str, *, runs_dir: str | None = None) -> dict[str, Any]:
        return self.get_run(run_id, runs_dir=runs_dir)

    def wait_for_run(
        self,
        run_id: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = 2.0,
        runs_dir: str | None = None,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        last_run: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            run = self.poll_run(run_id, runs_dir=runs_dir)
            last_run = run
            status = run.get("status")
            if status == "completed":
                return run
            if status == "failed":
                error = run.get("error") if isinstance(run.get("error"), dict) else {}
                raise OcrApiError(
                    422,
                    str(error.get("code") or "RUN_FAILED"),
                    str(error.get("message") or "Run failed"),
                    {"run": run},
                )
            time.sleep(max(poll_interval_seconds, 0.1))
        raise OcrApiError(
            408,
            "RUN_TIMEOUT",
            f"Run did not complete within {timeout_seconds} seconds",
            {"run": last_run} if last_run else None,
        )

    def get_run_result(self, run_id: str, *, runs_dir: str | None = None) -> dict[str, Any]:
        return self._get_run_json(f"/v1/runs/{run_id}/result", runs_dir=runs_dir)

    def get_run_trace(self, run_id: str, *, runs_dir: str | None = None) -> dict[str, Any]:
        return self._get_run_json(f"/v1/runs/{run_id}/trace", runs_dir=runs_dir)

    def list_run_artifacts(
        self,
        run_id: str,
        *,
        limit: int = 200,
        runs_dir: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if runs_dir:
            params["runs_dir"] = runs_dir
        response = self.session.get(
            self._url(f"/v1/runs/{run_id}/artifacts"),
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        return self._json_response(response)

    def get_artifact(
        self,
        run_id: str,
        artifact_name: str,
        *,
        runs_dir: str | None = None,
    ) -> dict[str, Any]:
        params = {"runs_dir": runs_dir} if runs_dir else None
        response = self.session.get(
            self._url(f"/v1/runs/{run_id}/artifacts/{artifact_name}"),
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_error(response)
        content_type = response.headers.get("content-type")
        return {
            "run_id": run_id,
            "artifact_name": artifact_name,
            "content_type": content_type,
            "size_bytes": len(response.content),
            "content_base64": base64.b64encode(response.content).decode("ascii"),
        }

    def _get_run_json(self, path: str, *, runs_dir: str | None = None) -> dict[str, Any]:
        params = {"runs_dir": runs_dir} if runs_dir else None
        response = self.session.get(
            self._url(path),
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        return self._json_response(response)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    def _json_response(self, response: requests.Response) -> dict[str, Any]:
        self._raise_for_error(response)
        try:
            payload = response.json()
        except ValueError as exc:
            raise OcrApiError(
                response.status_code,
                "INVALID_API_RESPONSE",
                "OCR API did not return valid JSON",
            ) from exc
        if not isinstance(payload, dict):
            raise OcrApiError(
                response.status_code,
                "INVALID_API_RESPONSE",
                "OCR API JSON response must be an object",
            )
        return payload

    def _raise_for_error(self, response: requests.Response) -> None:
        if response.status_code < 400:
            return
        code = f"HTTP_{response.status_code}"
        message = response.text or "OCR API request failed"
        details = None
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if not isinstance(error, dict):
                detail = payload.get("detail")
                if isinstance(detail, dict):
                    error = detail.get("error")
            if isinstance(error, dict):
                code = str(error.get("code") or code)
                message = str(error.get("message") or message)
                raw_details = error.get("details")
                details = raw_details if isinstance(raw_details, dict) else None
        raise OcrApiError(response.status_code, code, message, details)
