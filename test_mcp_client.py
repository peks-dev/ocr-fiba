from __future__ import annotations

import base64
import unittest
from typing import Any

from adapters.mcp.client import DEFAULT_TIMEOUT_SECONDS, OcrApiClient, OcrApiError
from adapters.mcp.tools import process_api_response


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


class FakeSession:
    def __init__(self, response: "FakeResponse") -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs) -> "FakeResponse":
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return self.response

    def get(self, url: str, **kwargs) -> "FakeResponse":
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self.response


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
