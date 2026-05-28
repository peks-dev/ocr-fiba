from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from api.main import create_app
from api.routes.runs import get_run, get_run_artifact, get_run_result, get_run_trace


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


if __name__ == "__main__":
    unittest.main()
