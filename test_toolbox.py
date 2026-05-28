from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config.pipeline_config import PipelineConfig
from core.toolbox import OcrToolbox
from providers.base import TokenUsage
from validation import ValidationEngine


class ToolboxTest(unittest.TestCase):
    def test_build_and_validate_return_tool_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolbox = OcrToolbox.__new__(OcrToolbox)
            toolbox.config = PipelineConfig(
                cropper_provider="gemini",
                cropper_model="crop-model",
                extractor_provider="docstrange",
                extractor_model="extract-model",
            )
            toolbox.validation_engine = ValidationEngine(plugins=[])
            context = toolbox.create_context(
                Path("sheet.jpg"),
                Path(tmp),
                run_id="run_test",
            )

            extracted = {
                "header": {},
                "team_a": {},
                "team_b": {},
                "team_a_fouls": {},
                "team_b_fouls": {},
                "progressive_score": {},
                "footer": {},
            }

            built = toolbox.build_final_output(
                context,
                extracted,
                processing_time_ms=42,
                token_usage=TokenUsage(total_tokens=10),
            )
            validated = toolbox.validate_result(context, built.data["result"])

            self.assertTrue(built.success)
            self.assertTrue(validated.success)
            self.assertEqual(validated.data["result"]["match_status"], "success")
            self.assertEqual(
                built.data["result"]["meta"]["cropper"],
                "gemini:crop-model",
            )
            self.assertTrue(context.trace_path.exists())

            payload = json.loads(context.trace_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "run_test")
            self.assertEqual(payload["steps"][-1]["step"], "validate_result")


if __name__ == "__main__":
    unittest.main()
