from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.responses import FileResponse

from api.main import create_app
from api.routes.pipeline import _parse_options_json, upload_and_run_full_pipeline
from api.routes.runs import get_run, get_run_artifact, get_run_result, get_run_trace
from core.types import Artifact, RunContext, ToolResult


class ApiTest(unittest.TestCase):
    def test_create_app_registers_health(self) -> None:
        app = create_app()

        routes = {getattr(route, "path", "") for route in app.routes}
        self.assertIn("/health", routes)

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
            artifact_response = get_run_artifact("run_test", "header.png", runs_dir=tmp)

            self.assertTrue(run_response["has_trace"])
            self.assertEqual(trace_response["run_id"], "run_test")
            self.assertEqual(result_response["match_status"], "success")
            self.assertIsInstance(artifact_response, FileResponse)
            self.assertEqual(Path(artifact_response.path).read_bytes(), b"image")

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
