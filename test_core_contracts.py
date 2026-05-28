from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.artifacts import ArtifactStore
from core.tracing import RunTracer
from core.types import ProviderUsage, RunContext, ToolResult


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
                step.complete(output={"processed_image": "input.jpg"})

            tracer.write()

            payload = json.loads(context.trace_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "run_test")
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


if __name__ == "__main__":
    unittest.main()
