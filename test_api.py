from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.responses import FileResponse

from api.auth import is_auth_exempt, is_authorized, unauthorized_response
from api.main import create_app
from api.responses import sanitize_for_public_response
from api.routes.pipeline import _parse_options_json, upload_and_run_full_pipeline
from api.routes.runs import (
    list_runs,
    delete_run,
    get_run,
    get_run_artifact,
    get_run_result,
    get_run_trace,
    list_run_artifacts,
)
from api.settings import get_api_settings, resolve_runs_dir
from core.types import Artifact, RunContext, ToolResult


class ApiTest(unittest.TestCase):
    def test_create_app_registers_health(self) -> None:
        app = create_app()

        routes = {getattr(route, "path", "") for route in app.routes}
        self.assertIn("/health", routes)

    def test_health_is_auth_exempt(self) -> None:
        self.assertTrue(is_auth_exempt("/health"))
        self.assertFalse(is_auth_exempt("/v1/runs"))

    def test_api_key_auth_allows_local_mode_without_expected_key(self) -> None:
        self.assertTrue(is_authorized("", None))

    def test_api_key_auth_rejects_missing_or_invalid_bearer_token(self) -> None:
        self.assertFalse(is_authorized("", "secret"))
        self.assertFalse(is_authorized("Bearer wrong", "secret"))
        self.assertFalse(is_authorized("Basic secret", "secret"))

    def test_api_key_auth_accepts_valid_bearer_token(self) -> None:
        self.assertTrue(is_authorized("Bearer secret", "secret"))

    def test_unauthorized_response_uses_standard_error_shape(self) -> None:
        response = unauthorized_response()
        payload = json.loads(response.body.decode("utf-8"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(payload["success"], False)
        self.assertEqual(payload["error"]["code"], "UNAUTHORIZED")

    def test_production_requires_api_key(self) -> None:
        with patch.dict("os.environ", {"OCR_ENV": "production"}, clear=True):
            with self.assertRaises(RuntimeError) as exc:
                get_api_settings()

        self.assertIn("OCR_ENGINE_API_KEY", str(exc.exception))

    def test_resolve_runs_dir_uses_requested_path_in_development(self) -> None:
        with patch.dict("os.environ", {"OCR_ENV": "development"}, clear=True):
            self.assertEqual(resolve_runs_dir("/tmp/dev-runs"), Path("/tmp/dev-runs"))

    def test_default_max_upload_mb_is_20(self) -> None:
        with patch.dict("os.environ", {"OCR_ENV": "development"}, clear=True):
            settings = get_api_settings()

        self.assertEqual(settings.max_upload_mb, 20)
        self.assertEqual(settings.max_upload_bytes, 20 * 1024 * 1024)

    def test_max_upload_mb_can_be_overridden(self) -> None:
        with patch.dict("os.environ", {"OCR_MAX_UPLOAD_MB": "5"}, clear=True):
            settings = get_api_settings()

        self.assertEqual(settings.max_upload_mb, 5)
        self.assertEqual(settings.max_upload_bytes, 5 * 1024 * 1024)

    def test_max_upload_mb_must_be_positive(self) -> None:
        with patch.dict("os.environ", {"OCR_MAX_UPLOAD_MB": "0"}, clear=True):
            with self.assertRaises(RuntimeError) as exc:
                get_api_settings()

        self.assertIn("OCR_MAX_UPLOAD_MB", str(exc.exception))

    def test_resolve_runs_dir_ignores_requested_path_in_production(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "OCR_ENV": "production",
                "OCR_ENGINE_API_KEY": "secret",
                "OCR_RUNS_DIR": "/srv/ocr-runs",
            },
            clear=True,
        ):
            self.assertEqual(resolve_runs_dir("/tmp/user-controlled"), Path("/srv/ocr-runs"))

    def test_public_response_sanitizer_keeps_paths_in_development(self) -> None:
        payload = {
            "run_id": "run_test",
            "run_dir": "/tmp/runs/run_test",
            "artifacts": [{"name": "header.png", "path": "/tmp/header.png"}],
        }

        with patch.dict("os.environ", {"OCR_ENV": "development"}, clear=True):
            sanitized = sanitize_for_public_response(payload)

        self.assertEqual(sanitized["run_dir"], "/tmp/runs/run_test")
        self.assertEqual(sanitized["artifacts"][0]["path"], "/tmp/header.png")

    def test_public_response_sanitizer_removes_paths_in_production(self) -> None:
        payload = {
            "run_id": "run_test",
            "run_dir": "/tmp/runs/run_test",
            "input_dir": "/tmp/runs/run_test/input",
            "artifacts_dir": "/tmp/runs/run_test/artifacts",
            "trace_path": "/tmp/runs/run_test/trace.json",
            "result_path": "/tmp/runs/run_test/result.json",
            "artifacts": [{"name": "header.png", "path": "/tmp/header.png"}],
            "data": {
                "result_path": "/tmp/runs/run_test/result.json",
                "trace_path": "/tmp/runs/run_test/trace.json",
            },
        }

        with patch.dict(
            "os.environ",
            {"OCR_ENV": "production", "OCR_ENGINE_API_KEY": "secret"},
            clear=True,
        ):
            sanitized = sanitize_for_public_response(payload)

        self.assertNotIn("run_dir", sanitized)
        self.assertNotIn("input_dir", sanitized)
        self.assertNotIn("artifacts_dir", sanitized)
        self.assertNotIn("trace_path", sanitized)
        self.assertNotIn("result_path", sanitized)
        self.assertNotIn("path", sanitized["artifacts"][0])
        self.assertNotIn("result_path", sanitized["data"])
        self.assertNotIn("trace_path", sanitized["data"])
        self.assertEqual(sanitized["links"]["result"], "/v1/runs/run_test/result")

    def test_unexpected_errors_return_standard_json(self) -> None:
        app = create_app()
        handler = app.exception_handlers[Exception]

        response = run_async(handler(None, RuntimeError("secret internal detail")))
        payload = json.loads(response.body.decode("utf-8"))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload["success"], False)
        self.assertEqual(payload["error"]["code"], "INTERNAL_SERVER_ERROR")
        self.assertEqual(payload["error"]["message"], "Internal server error")
        self.assertNotIn("secret internal detail", json.dumps(payload))

    def test_get_run_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_test"
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir(parents=True)
            (run_dir / "trace.json").write_text(
                json.dumps({"run_id": "run_test", "steps": []}),
                encoding="utf-8",
            )
            (run_dir / "result.json").write_text(
                json.dumps({"match_status": "success"}),
                encoding="utf-8",
            )
            (artifacts_dir / "header.png").write_bytes(b"image")

            run_response = get_run("run_test", runs_dir=tmp)
            trace_response = get_run_trace("run_test", runs_dir=tmp)
            result_response = get_run_result("run_test", runs_dir=tmp)
            artifacts_response = list_run_artifacts("run_test", runs_dir=tmp)
            artifact_response = get_run_artifact("run_test", "header.png", runs_dir=tmp)

            self.assertTrue(run_response["has_trace"])
            self.assertTrue(run_response["has_result"])
            self.assertEqual(run_response["match_status"], "success")
            self.assertEqual(run_response["artifacts_count"], 1)
            self.assertEqual(run_response["artifacts"][0]["name"], "header.png")
            self.assertEqual(trace_response["run_id"], "run_test")
            self.assertEqual(result_response["match_status"], "success")
            self.assertEqual(artifacts_response["count"], 1)
            self.assertEqual(artifacts_response["artifacts"][0]["name"], "header.png")
            self.assertEqual(artifacts_response["artifacts"][0]["size_bytes"], 5)
            self.assertIsInstance(artifact_response, FileResponse)
            self.assertEqual(Path(artifact_response.path).read_bytes(), b"image")

    def test_list_run_artifacts_returns_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "run_test" / "artifacts"
            nested_dir = artifacts_dir / "crops"
            nested_dir.mkdir(parents=True)
            (artifacts_dir / "header.png").write_bytes(b"image")
            (nested_dir / "team.png").write_bytes(b"team")

            response = list_run_artifacts("run_test", runs_dir=tmp)

            self.assertEqual(response["count"], 2)
            self.assertEqual(
                [artifact["name"] for artifact in response["artifacts"]],
                ["crops/team.png", "header.png"],
            )

    def test_list_run_artifacts_missing_run_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(HTTPException) as exc:
                list_run_artifacts("missing", runs_dir=tmp)

            self.assertEqual(exc.exception.status_code, 404)
            self.assertEqual(exc.exception.detail["error"]["code"], "RUN_NOT_FOUND")

    def test_delete_run_removes_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_test"
            (run_dir / "artifacts").mkdir(parents=True)
            (run_dir / "artifacts" / "header.png").write_bytes(b"image")

            response = delete_run("run_test", runs_dir=tmp)

            self.assertTrue(response["success"])
            self.assertTrue(response["deleted"])
            self.assertEqual(response["run_id"], "run_test")
            self.assertFalse(run_dir.exists())

    def test_delete_run_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(HTTPException) as exc:
                delete_run("../outside", runs_dir=tmp)

            self.assertEqual(exc.exception.status_code, 400)
            self.assertEqual(exc.exception.detail["error"]["code"], "INVALID_RUN_ID")

    def test_list_runs_returns_run_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_test"
            input_dir = run_dir / "input"
            input_dir.mkdir(parents=True)
            (input_dir / "sheet.jpg").write_bytes(b"image")
            (run_dir / "trace.json").write_text(
                json.dumps({"run_id": "run_test", "steps": []}),
                encoding="utf-8",
            )
            (run_dir / "result.json").write_text(
                json.dumps({"match_status": "success"}),
                encoding="utf-8",
            )

            response = list_runs(runs_dir=tmp)

            self.assertEqual(response["count"], 1)
            self.assertEqual(response["runs"][0]["run_id"], "run_test")
            self.assertTrue(response["runs"][0]["has_trace"])
            self.assertTrue(response["runs"][0]["has_result"])
            self.assertEqual(response["runs"][0]["match_status"], "success")
            self.assertEqual(response["runs"][0]["input_files"], ["sheet.jpg"])

    def test_list_runs_missing_directory_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            response = list_runs(runs_dir=str(Path(tmp) / "missing"))

            self.assertEqual(response["count"], 0)
            self.assertEqual(response["runs"], [])

    def test_artifact_path_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_test" / "artifacts"
            run_dir.mkdir(parents=True)

            with self.assertRaises(HTTPException) as exc:
                get_run_artifact("run_test", "../result.json", runs_dir=tmp)
            self.assertEqual(exc.exception.status_code, 400)
            self.assertEqual(exc.exception.detail["error"]["code"], "INVALID_ARTIFACT_PATH")

    def test_parse_options_json_rejects_invalid_json(self) -> None:
        with self.assertRaises(HTTPException) as exc:
            _parse_options_json("{invalid")
        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(exc.exception.detail["error"]["code"], "INVALID_OPTIONS_JSON")

    def test_upload_pipeline_saves_file_and_returns_tool_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_file = FakeUploadFile("sheet.jpg", b"image")

            with patch("api.routes.pipeline.OcrToolbox", FakeToolbox):
                response = run_async(
                    upload_and_run_full_pipeline(
                        file=fake_file,
                        run_id="run_test",
                        runs_dir=tmp,
                        options_json=None,
                    )
                )

            input_path = Path(tmp) / "run_test" / "input" / "sheet.jpg"
            self.assertTrue(input_path.exists())
            self.assertEqual(input_path.read_bytes(), b"image")
            self.assertTrue(response["success"])
            self.assertEqual(response["run_id"], "run_test")
            self.assertEqual(response["data"]["result_path"], str(Path(tmp) / "run_test" / "result.json"))

    def test_upload_pipeline_rejects_large_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_test"
            fake_file = FakeUploadFile("sheet.jpg", b"x" * (1024 * 1024 + 1))

            with patch.dict("os.environ", {"OCR_MAX_UPLOAD_MB": "1"}, clear=True):
                with patch("api.routes.pipeline.OcrToolbox", FakeToolbox):
                    with self.assertRaises(HTTPException) as exc:
                        run_async(
                            upload_and_run_full_pipeline(
                                file=fake_file,
                                run_id="run_test",
                                runs_dir=tmp,
                                options_json=None,
                            )
                        )

        self.assertEqual(exc.exception.status_code, 413)
        self.assertEqual(exc.exception.detail["error"]["code"], "UPLOAD_TOO_LARGE")
        self.assertFalse(run_dir.exists())

    def test_upload_pipeline_uses_server_runs_dir_in_production(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server_runs_dir = Path(tmp) / "server-runs"
            user_runs_dir = Path(tmp) / "user-controlled"
            fake_file = FakeUploadFile("sheet.jpg", b"image")

            with patch.dict(
                "os.environ",
                {
                    "OCR_ENV": "production",
                    "OCR_ENGINE_API_KEY": "secret",
                    "OCR_RUNS_DIR": str(server_runs_dir),
                },
                clear=True,
            ):
                with patch("api.routes.pipeline.OcrToolbox", FakeToolbox):
                    response = run_async(
                        upload_and_run_full_pipeline(
                            file=fake_file,
                            run_id="run_test",
                            runs_dir=str(user_runs_dir),
                            options_json=None,
                        )
                    )

            self.assertTrue((server_runs_dir / "run_test" / "input" / "sheet.jpg").exists())
            self.assertFalse(user_runs_dir.exists())
            self.assertTrue((server_runs_dir / "run_test" / "result.json").exists())
            self.assertNotIn("result_path", response["data"])

    def test_upload_pipeline_sanitizes_paths_in_production(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server_runs_dir = Path(tmp) / "server-runs"
            fake_file = FakeUploadFile("sheet.jpg", b"image")

            with patch.dict(
                "os.environ",
                {
                    "OCR_ENV": "production",
                    "OCR_ENGINE_API_KEY": "secret",
                    "OCR_RUNS_DIR": str(server_runs_dir),
                },
                clear=True,
            ):
                with patch("api.routes.pipeline.OcrToolbox", FakeToolbox):
                    response = run_async(
                        upload_and_run_full_pipeline(
                            file=fake_file,
                            run_id="run_test",
                            runs_dir="/tmp/user-controlled",
                            options_json=None,
                        )
                    )

            self.assertTrue(response["success"])
            self.assertEqual(response["run_id"], "run_test")
            self.assertIn("links", response)
            self.assertNotIn("result_path", response["data"])
            self.assertNotIn("trace_path", response["data"])
            self.assertNotIn("artifacts_dir", response["data"])
            self.assertNotIn("path", response["artifacts"][0])


class FakeToolbox:
    def __init__(self, config) -> None:
        self.config = config

    def create_context(self, image_path, output_dir=None, *, run_id=None, runs_dir=Path("runs"), use_run_layout=False):
        return RunContext.create_run(Path(image_path), Path(runs_dir), run_id=run_id)

    def run_full_pipeline(self, image_path, output_dir=None, *, run_id=None, runs_dir=Path("runs"), use_run_layout=False):
        context = RunContext.create_run(Path(image_path), Path(runs_dir), run_id=run_id)
        context.ensure_dirs()
        context.result_path.write_text(json.dumps({"match_status": "success"}), encoding="utf-8")
        context.trace_path.write_text(json.dumps({"run_id": context.run_id, "steps": []}), encoding="utf-8")
        return ToolResult(
            success=True,
            run_id=context.run_id,
            step="run_full_pipeline",
            status="completed",
            data={
                "result": {"match_status": "success"},
                "result_path": context.result_path,
                "trace_path": context.trace_path,
                "artifacts_dir": context.artifacts_dir,
            },
            artifacts=[
                Artifact(name="result.json", path=context.result_path, kind="result"),
            ],
        )


def run_async(coro):
    import asyncio

    return asyncio.run(coro)


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


if __name__ == "__main__":
    unittest.main()
