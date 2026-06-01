from __future__ import annotations

import base64
import unittest
from typing import Any

from ocr_engine_mcp.client import DEFAULT_TIMEOUT_SECONDS, OcrApiClient, OcrApiError
from ocr_engine_mcp.tools import process_api_response, submit_scoresheet_base64, wait_for_run


class OcrApiClientTest(unittest.TestCase):
    def test_default_timeout_is_300_seconds(self) -> None:
        self.assertEqual(DEFAULT_TIMEOUT_SECONDS, 300)

    def test_run_full_pipeline_posts_json(self) -> None:
        session = FakeSession(
            FakeResponse(
                200,
                {
                    "success": True,
                    "run_id": "run_test",
                    "status": "completed",
                    "data": {"result": {"match_status": "success"}},
                },
            )
        )
        client = OcrApiClient("http://api.test", api_key="secret", session=session)

        response = client.run_full_pipeline(
            "/data/sheet.jpg",
            run_id="run_test",
            options={"gamma": 0.7},
        )

        self.assertTrue(response["success"])
        self.assertEqual(session.calls[0]["method"], "POST")
        self.assertEqual(session.calls[0]["url"], "http://api.test/v1/pipeline/full")
        self.assertEqual(session.calls[0]["json"]["image_path"], "/data/sheet.jpg")
        self.assertEqual(session.calls[0]["headers"]["Authorization"], "Bearer secret")

    def test_upload_scoresheet_base64_posts_multipart(self) -> None:
        session = FakeSession(FakeResponse(200, {"success": True, "run_id": "run_upload"}))
        client = OcrApiClient("http://api.test", session=session)

        response = client.upload_scoresheet_base64(
            base64.b64encode(b"image").decode("ascii"),
            filename="sheet.jpg",
            run_id="run_upload",
            options={"grid_removal": False},
        )

        self.assertEqual(response["run_id"], "run_upload")
        call = session.calls[0]
        self.assertEqual(call["url"], "http://api.test/v1/pipeline/full/upload")
        self.assertEqual(call["data"]["run_id"], "run_upload")
        self.assertIn("options_json", call["data"])
        self.assertEqual(call["files"]["file"][0], "sheet.jpg")

    def test_submit_scoresheet_base64_posts_async_multipart(self) -> None:
        session = FakeSession(FakeResponse(200, {"success": True, "run_id": "run_async", "status": "queued"}))
        client = OcrApiClient("http://api.test", session=session)

        response = client.submit_scoresheet_base64(
            base64.b64encode(b"image").decode("ascii"),
            filename="sheet.jpg",
            run_id="run_async",
            options={"grid_removal": False},
        )

        self.assertEqual(response["run_id"], "run_async")
        call = session.calls[0]
        self.assertEqual(call["url"], "http://api.test/v1/runs/upload")
        self.assertEqual(call["data"]["run_id"], "run_async")
        self.assertIn("options_json", call["data"])
        self.assertEqual(call["files"]["file"][0], "sheet.jpg")

    def test_submit_scoresheet_from_path_posts_async_json(self) -> None:
        session = FakeSession(FakeResponse(200, {"success": True, "run_id": "run_async", "status": "queued"}))
        client = OcrApiClient("http://api.test", session=session)

        response = client.submit_scoresheet_from_path(
            "/data/sheet.jpg",
            run_id="run_async",
            options={"gamma": 0.7},
        )

        self.assertEqual(response["status"], "queued")
        call = session.calls[0]
        self.assertEqual(call["url"], "http://api.test/v1/runs")
        self.assertEqual(call["json"]["image_path"], "/data/sheet.jpg")
        self.assertEqual(call["json"]["run_id"], "run_async")

    def test_poll_run_gets_run_status(self) -> None:
        session = FakeSession(FakeResponse(200, {"run_id": "run_async", "status": "running"}))
        client = OcrApiClient("http://api.test", session=session)

        response = client.poll_run("run_async")

        self.assertEqual(response["status"], "running")
        self.assertEqual(session.calls[0]["method"], "GET")
        self.assertEqual(session.calls[0]["url"], "http://api.test/v1/runs/run_async")

    def test_wait_for_run_returns_completed(self) -> None:
        session = FakeSession(
            [
                FakeResponse(200, {"run_id": "run_async", "status": "running"}),
                FakeResponse(200, {"run_id": "run_async", "status": "completed"}),
            ]
        )
        client = OcrApiClient("http://api.test", session=session)

        response = client.wait_for_run("run_async", timeout_seconds=1, poll_interval_seconds=0.1)

        self.assertEqual(response["status"], "completed")
        self.assertEqual(len(session.calls), 2)

    def test_wait_for_run_raises_on_failed(self) -> None:
        session = FakeSession(FakeResponse(200, {"run_id": "run_async", "status": "failed", "error": {"code": "PIPELINE_FAILED"}}))
        client = OcrApiClient("http://api.test", session=session)

        with self.assertRaises(OcrApiError) as exc:
            client.wait_for_run("run_async", timeout_seconds=1, poll_interval_seconds=0.1)

        self.assertEqual(exc.exception.status_code, 422)
        self.assertEqual(exc.exception.code, "PIPELINE_FAILED")

    def test_wait_for_run_raises_on_timeout(self) -> None:
        session = FakeSession(FakeResponse(200, {"run_id": "run_async", "status": "running"}))
        client = OcrApiClient("http://api.test", session=session)

        with self.assertRaises(OcrApiError) as exc:
            client.wait_for_run("run_async", timeout_seconds=0.01, poll_interval_seconds=0.1)

        self.assertEqual(exc.exception.status_code, 408)
        self.assertEqual(exc.exception.code, "RUN_TIMEOUT")

    def test_invalid_base64_raises_structured_error(self) -> None:
        client = OcrApiClient("http://api.test", session=FakeSession(FakeResponse(200, {})))

        with self.assertRaises(OcrApiError) as exc:
            client.upload_scoresheet_base64("not-valid-base64")

        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(exc.exception.code, "INVALID_IMAGE_BASE64")

    def test_api_error_extracts_fastapi_error_shape(self) -> None:
        session = FakeSession(
            FakeResponse(
                404,
                {
                    "detail": {
                        "success": False,
                        "error": {"code": "RUN_NOT_FOUND", "message": "Run not found"},
                    }
                },
            )
        )
        client = OcrApiClient("http://api.test", session=session)

        with self.assertRaises(OcrApiError) as exc:
            client.get_run("missing")

        self.assertEqual(exc.exception.status_code, 404)
        self.assertEqual(exc.exception.code, "RUN_NOT_FOUND")
        self.assertEqual(exc.exception.message, "Run not found")

    def test_process_api_response_returns_agent_friendly_summary(self) -> None:
        response = process_api_response(
            {
                "success": True,
                "run_id": "run_test",
                "status": "completed",
                "data": {
                    "result": {
                        "match_status": "needs_review",
                        "validation_warnings": [{"type": "score_mismatch"}],
                        "meta": {"total_tokens": 10},
                    },
                    "result_path": "runs/run_test/result.json",
                    "trace_path": "runs/run_test/trace.json",
                },
            }
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["summary"]["match_status"], "needs_review")
        self.assertEqual(response["resources"]["result"], "result://run_test")
        self.assertIn("Review validation warnings before trusting the extraction.", response["next_actions"])

    def test_submit_tool_returns_agent_friendly_next_actions(self) -> None:
        client = OcrApiClient(
            "http://api.test",
            session=FakeSession(FakeResponse(200, {"success": True, "run_id": "run_async", "status": "queued"})),
        )

        response = submit_scoresheet_base64(client, base64.b64encode(b"image").decode("ascii"))

        self.assertTrue(response["success"])
        self.assertEqual(response["status"], "queued")
        self.assertEqual(response["resources"]["run"], "run://run_async")
        self.assertIn("Poll run status with poll_run.", response["next_actions"])

    def test_wait_tool_returns_failed_status_without_raising(self) -> None:
        client = OcrApiClient(
            "http://api.test",
            session=FakeSession(FakeResponse(200, {"run_id": "run_async", "status": "failed", "error": {"code": "PIPELINE_FAILED"}})),
        )

        response = wait_for_run(client, "run_async", timeout_seconds=1, poll_interval_seconds=0.1)

        self.assertFalse(response["success"])
        self.assertEqual(response["status"], "failed")


class FakeSession:
    def __init__(self, response: "FakeResponse | list[FakeResponse]") -> None:
        self.responses = response if isinstance(response, list) else [response]
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs) -> "FakeResponse":
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return self._response()

    def get(self, url: str, **kwargs) -> "FakeResponse":
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self._response()

    def _response(self) -> "FakeResponse":
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[index]


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any],
        *,
        content: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.headers = headers or {}
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


if __name__ == "__main__":
    unittest.main()
