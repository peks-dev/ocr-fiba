from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.artifacts import ArtifactStore
from core.tracing import RunTracer
from core.types import Artifact, ProviderUsage, RunContext, ToolResult


class CoreContractsTest(unittest.TestCase):
    def test_tool_result_is_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = RunContext.create(
                Path("input.jpg"),
                Path(tmp),
                run_id="run_test",
            )
            result = ToolResult(
                success=True,
                run_id=context.run_id,
                step="extract_section",
                status="completed",
                data={"section": "header"},
                usage=ProviderUsage(
                    provider="docstrange",
                    model="nanonets-ocr-3",
                    total_tokens=123,
                ),
            )

            payload = result.to_dict()
            self.assertEqual(payload["run_id"], "run_test")
            self.assertEqual(payload["usage"]["total_tokens"], 123)
            json.dumps(payload)

    def test_tracer_writes_trace_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = RunContext.create(
                Path("input.jpg"),
                Path(tmp),
                run_id="run_test",
            )
            tracer = RunTracer(context)

            with tracer.step("preprocess_sheet") as step:
                step.complete(
                    output={"processed_image": "input.jpg"},
                    artifacts=[Artifact(name="input.jpg", path=Path("input.jpg"))],
                    usage=ProviderUsage(provider="docstrange", model="nanonets-ocr-3", total_tokens=123),
                )
            tracer.set_result_summary({"match_status": "success"})

            tracer.write()

            payload = json.loads(context.trace_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "run_test")
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["step_count"], 1)
            self.assertEqual(payload["artifact_count"], 1)
            self.assertEqual(payload["total_usage"]["total_tokens"], 123)
            self.assertEqual(payload["result_summary"]["match_status"], "success")
            self.assertIsNotNone(payload["started_at_iso"])
            self.assertIsNotNone(payload["completed_at_iso"])
            self.assertEqual(payload["steps"][0]["step"], "preprocess_sheet")
            self.assertEqual(payload["steps"][0]["status"], "completed")

    def test_artifact_store_writes_json_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = RunContext.create(
                Path("input.jpg"),
                Path(tmp),
                run_id="run_test",
            )
            store = ArtifactStore(context)

            artifact = store.write_json("sample.json", {"ok": True})

            self.assertTrue((Path(tmp) / "sample.json").exists())
            self.assertEqual(artifact.name, "sample.json")
            self.assertEqual(store.to_list()[0]["kind"], "json")

    def test_run_context_can_create_canonical_run_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = RunContext.create_run(
                Path("input.jpg"),
                Path(tmp),
                run_id="run_test",
            )
            context.ensure_dirs()

            run_dir = Path(tmp) / "run_test"
            self.assertEqual(context.layout, "run")
            self.assertEqual(context.run_dir, run_dir)
            self.assertEqual(context.input_dir, run_dir / "input")
            self.assertEqual(context.artifacts_dir, run_dir / "artifacts")
            self.assertEqual(context.raw_dir, run_dir / "raw")
            self.assertEqual(context.trace_path, run_dir / "trace.json")
            self.assertEqual(context.result_path, run_dir / "result.json")
            self.assertTrue(context.input_dir.exists())
            self.assertTrue(context.artifacts_dir.exists())
            self.assertTrue(context.raw_dir.exists())

    def test_artifact_store_copies_input_and_writes_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.jpg"
            source.write_bytes(b"image")
            context = RunContext.create_run(source, Path(tmp) / "runs", run_id="run_test")
            store = ArtifactStore(context)

            input_artifact = store.copy_input()
            result_artifact = store.write_result({"ok": True})

            self.assertTrue((context.input_dir / "source.jpg").exists())
            self.assertTrue(context.result_path.exists())
            self.assertEqual(input_artifact.kind, "input")
            self.assertEqual(result_artifact.kind, "result")
            self.assertEqual(json.loads(context.result_path.read_text(encoding="utf-8")), {"ok": True})


if __name__ == "__main__":
    unittest.main()
