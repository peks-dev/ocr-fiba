from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ocr_engine_api.services.run_repository import RunRepository, RunRepositoryError


class RunRepositoryTest(unittest.TestCase):
    def test_list_runs_returns_summaries(self) -> None:
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

            response = RunRepository(tmp).list_runs()

            self.assertEqual(response["count"], 1)
            self.assertEqual(response["runs"][0]["run_id"], "run_test")
            self.assertEqual(response["runs"][0]["match_status"], "success")
            self.assertEqual(response["runs"][0]["input_files"], ["sheet.jpg"])

    def test_get_run_includes_artifacts_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "run_test" / "artifacts"
            artifacts_dir.mkdir(parents=True)
            (artifacts_dir / "header.png").write_bytes(b"image")
            (artifacts_dir.parent / "result.json").write_text(
                json.dumps({"match_status": "needs_review"}),
                encoding="utf-8",
            )

            response = RunRepository(tmp).get_run("run_test")

            self.assertEqual(response["run_id"], "run_test")
            self.assertEqual(response["match_status"], "needs_review")
            self.assertEqual(response["artifacts_count"], 1)
            self.assertEqual(response["artifacts"][0]["name"], "header.png")

    def test_get_trace_and_result_read_json_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_test"
            run_dir.mkdir()
            (run_dir / "trace.json").write_text(
                json.dumps({"run_id": "run_test"}),
                encoding="utf-8",
            )
            (run_dir / "result.json").write_text(
                json.dumps({"match_status": "success"}),
                encoding="utf-8",
            )
            repository = RunRepository(tmp)

            self.assertEqual(repository.get_trace("run_test")["run_id"], "run_test")
            self.assertEqual(repository.get_result("run_test")["match_status"], "success")

    def test_status_lifecycle_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repository = RunRepository(tmp)

            created = repository.create_status("run_test")
            running = repository.update_status(
                "run_test",
                status="running",
                progress={"current_step": "preprocess_sheet", "completed_steps": [], "step_count": None},
            )
            completed = repository.update_status("run_test", status="completed")

            self.assertEqual(created["status"], "queued")
            self.assertEqual(running["status"], "running")
            self.assertEqual(running["progress"]["current_step"], "preprocess_sheet")
            self.assertEqual(completed["status"], "completed")
            self.assertIsNotNone(completed["completed_at"])
            self.assertEqual(repository.get_status("run_test")["links"]["result"], "/v1/runs/run_test/result")

    def test_get_result_returns_409_for_active_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repository = RunRepository(tmp)
            repository.create_status("run_test")

            with self.assertRaises(RunRepositoryError) as exc:
                repository.get_result("run_test")

            self.assertEqual(exc.exception.status_code, 409)
            self.assertEqual(exc.exception.code, "RUN_NOT_COMPLETED")

    def test_get_result_returns_422_for_failed_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repository = RunRepository(tmp)
            repository.create_status("run_test")
            repository.update_status("run_test", status="failed", error={"code": "PIPELINE_FAILED"})

            with self.assertRaises(RunRepositoryError) as exc:
                repository.get_result("run_test")

            self.assertEqual(exc.exception.status_code, 422)
            self.assertEqual(exc.exception.code, "RUN_FAILED")

    def test_list_artifacts_returns_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "run_test" / "artifacts"
            nested_dir = artifacts_dir / "crops"
            nested_dir.mkdir(parents=True)
            (artifacts_dir / "header.png").write_bytes(b"image")
            (nested_dir / "team.png").write_bytes(b"team")

            response = RunRepository(tmp).list_artifacts("run_test")

            self.assertEqual(response["count"], 2)
            self.assertEqual(
                [artifact["name"] for artifact in response["artifacts"]],
                ["crops/team.png", "header.png"],
            )

    def test_resolve_artifact_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "run_test" / "artifacts"
            artifacts_dir.mkdir(parents=True)

            with self.assertRaises(RunRepositoryError) as exc:
                RunRepository(tmp).resolve_artifact("run_test", "../result.json")

            self.assertEqual(exc.exception.status_code, 400)
            self.assertEqual(exc.exception.code, "INVALID_ARTIFACT_PATH")

    def test_invalid_run_id_raises_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RunRepositoryError) as exc:
                RunRepository(tmp).get_run("../outside")

            self.assertEqual(exc.exception.status_code, 400)
            self.assertEqual(exc.exception.code, "INVALID_RUN_ID")

    def test_delete_run_removes_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_test"
            run_dir.mkdir()

            response = RunRepository(tmp).delete_run("run_test")

            self.assertTrue(response["success"])
            self.assertFalse(run_dir.exists())


if __name__ == "__main__":
    unittest.main()
