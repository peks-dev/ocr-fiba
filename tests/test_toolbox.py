from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import MethodType

from ocr_engine_core.config.pipeline_config import PipelineConfig
from ocr_engine_core.toolbox import OcrToolbox
from ocr_engine_core.types import ProviderUsage
from ocr_engine_core.types import ToolResult
from ocr_engine_core.providers.base import TokenUsage
from ocr_engine_core.validation import ValidationEngine


def toolbox_usage(usage: TokenUsage | None):
    if usage is None:
        return None
    return ProviderUsage.from_usage(usage)


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
            self.assertEqual(payload["status"], "completed")
            self.assertIn("total_usage", payload)
            self.assertEqual(payload["steps"][-1]["step"], "validate_result")

    def test_run_full_pipeline_is_single_orchestrator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "sheet.jpg"
            image_path.write_bytes(b"image")

            toolbox = OcrToolbox.__new__(OcrToolbox)
            toolbox.config = PipelineConfig(
                cropper_provider="gemini",
                cropper_model="crop-model",
                extractor_provider="docstrange",
                extractor_model="extract-model",
            )
            toolbox.validation_engine = ValidationEngine(plugins=[])

            def _tool_result(step: str, data: dict, usage: TokenUsage | None = None) -> ToolResult:
                return ToolResult(
                    success=True,
                    run_id="run_test",
                    step=step,
                    status="completed",
                    data=data,
                    usage=toolbox_usage(usage),
                )

            def preprocess(self, context, *, tracer=None):
                return _tool_result(
                    "preprocess_sheet",
                    {"processed_image": context.input_path, "used_fallback": True},
                )

            def detect(self, context, image_path, *, tracer=None):
                return _tool_result(
                    "detect_sections",
                    {"pixel_boxes": [], "sections": [], "meta": {}},
                    TokenUsage(total_tokens=2),
                )

            def crop_fouls(self, context, *, tracer=None):
                return _tool_result(
                    "crop_team_fouls",
                    {"pixel_boxes": [], "sections": [], "meta": {}},
                    TokenUsage(total_tokens=3),
                )

            def enhance(self, context, *, tracer=None):
                return _tool_result("enhance_sections", {"enhanced": []})

            def extract(self, context, *, tracer=None):
                return _tool_result(
                    "extract_sections",
                    {"extracted": {"header": {}}, "sections": ["header"]},
                    TokenUsage(total_tokens=5),
                )

            def build(self, context, extracted, *, processing_time_ms, token_usage, tracer=None):
                return _tool_result(
                    "build_final_output",
                    {"result": {"meta": {"total_tokens": token_usage.total_tokens}}},
                )

            def validate(self, context, result, *, tracer=None):
                result["match_status"] = "success"
                result["validation_warnings"] = []
                return _tool_result("validate_result", {"result": result})

            toolbox.preprocess_sheet = MethodType(preprocess, toolbox)
            toolbox.detect_sections = MethodType(detect, toolbox)
            toolbox.crop_team_fouls = MethodType(crop_fouls, toolbox)
            toolbox.enhance_sections = MethodType(enhance, toolbox)
            toolbox.extract_sections = MethodType(extract, toolbox)
            toolbox.build_final_output = MethodType(build, toolbox)
            toolbox.validate_result = MethodType(validate, toolbox)

            events = []
            result = toolbox.run_full_pipeline(
                image_path,
                runs_dir=Path(tmp) / "runs",
                run_id="run_test",
                use_run_layout=True,
                progress_callback=lambda event, payload: events.append((event, payload.get("step"))),
            )

            self.assertTrue(result.success)
            self.assertEqual(result.data["result"]["match_status"], "success")
            self.assertEqual(result.data["total_usage"].total_tokens, 10)
            self.assertTrue(result.data["result_path"].exists())
            self.assertTrue(result.data["trace_path"].exists())
            trace_payload = json.loads(result.data["trace_path"].read_text(encoding="utf-8"))
            self.assertEqual(trace_payload["result_summary"]["match_status"], "success")
            self.assertEqual(trace_payload["result_summary"]["total_tokens"], 10)
            self.assertEqual([artifact["kind"] for artifact in trace_payload["run_artifacts"]], ["input", "result"])
            self.assertIn(("step_start", "preprocess_sheet"), events)
            self.assertIn(("step_complete", "validate_result"), events)
            self.assertEqual([artifact.kind for artifact in result.artifacts], ["input", "result", "trace"])


if __name__ == "__main__":
    unittest.main()
