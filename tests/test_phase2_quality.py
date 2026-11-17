"""Unit tests for Phase 2 core-engine & CLI quality, security, and robustness improvements."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import MethodType
from unittest import mock

import cv2
import numpy as np

from ocr_engine_core.config.pipeline_config import (
    PipelineConfig,
    build_reasoning_config,
    parse_reasoning_config,
    resolve_default_extractor,
)
from ocr_engine_core.cropper import Cropper
from ocr_engine_core.exceptions import CroppingError, ErrorCode
from ocr_engine_core.output_builder import build_final_output
from ocr_engine_core.preprocessor import preprocess_sheet
from ocr_engine_core.providers.base import BoundingBox, PixelBox, TokenUsage
from ocr_engine_core.providers.gemini import GeminiProvider
from ocr_engine_core.providers.openrouter import OpenrouterProvider
from ocr_engine_core.toolbox import OcrToolbox
from ocr_engine_core.types import ProviderUsage, ToolResult
from ocr_engine_core.utils.team_markdown_parser import TeamMarkdownParseError, parse_mark_flag
from ocr_engine_core.validation import ValidationEngine


class PreprocessorSingleWriteTest(unittest.TestCase):
    def test_preprocess_sheet_enhances_in_memory_without_reopening_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "raw.jpg"
            dst = tmp_path / "out.jpg"

            # Synthetic dark background with a bright rectangular sheet contour
            canvas = np.zeros((1600, 1200, 3), dtype=np.uint8)
            cv2.rectangle(canvas, (100, 100), (1100, 1500), (245, 245, 245), thickness=-1)
            cv2.imwrite(str(src), canvas)

            with mock.patch("ocr_engine_core.preprocessor.Image.open") as open_mock:
                out = preprocess_sheet(src, dst)

            self.assertEqual(out, dst)
            self.assertTrue(dst.exists())
            open_mock.assert_not_called()


class CropperValidationTest(unittest.TestCase):
    def test_degenerate_box_raises_empty_crop_error(self) -> None:
        tiny = BoundingBox(name="header", x_min=100, y_min=100, x_max=101, y_max=101)
        with self.assertRaises(CroppingError) as ctx:
            Cropper._to_pixel_box(tiny, 1000, 1000)
        self.assertEqual(ctx.exception.code, ErrorCode.CROP_EMPTY_CROP)

    def test_layout_rejects_header_below_team_a(self) -> None:
        boxes = [
            PixelBox(name="header", x=0, y=200, width=800, height=100),
            PixelBox(name="team_a", x=0, y=150, width=500, height=300),
            PixelBox(name="team_b", x=0, y=500, width=500, height=300),
            PixelBox(name="progressive_score", x=550, y=150, width=300, height=650),
            PixelBox(name="footer", x=0, y=820, width=800, height=150),
        ]
        with self.assertRaises(CroppingError) as ctx:
            Cropper._validate_layout(boxes, 1000, 1000)
        self.assertEqual(ctx.exception.code, ErrorCode.CROP_LAYOUT_INVALID)


class ProviderHeadersTest(unittest.TestCase):
    def test_gemini_uses_header_instead_of_url_query_key(self) -> None:
        provider = GeminiProvider("gemini-2.5-flash", "secret-gemini-key")
        self.assertNotIn("secret-gemini-key", provider._request_url())
        self.assertEqual(provider._auth_headers().get("x-goog-api-key"), "secret-gemini-key")

    def test_openrouter_uses_project_referer(self) -> None:
        provider = OpenrouterProvider("google/gemini-4-carbon", "secret-or-key", reasoning={"effort": "low", "exclude": True})
        headers = provider._auth_headers()
        self.assertEqual(headers.get("HTTP-Referer"), "https://github.com/peks-dev/ocr-fiba")
        self.assertEqual(headers.get("X-OpenRouter-Title"), "ocr-fiba")
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "crop.png"
            img.write_bytes(b"png")
            payload = provider._build_payload(img, "extract")
        self.assertEqual(payload["model"], "google/gemini-4-carbon")
        self.assertEqual(payload["reasoning"], {"effort": "low", "exclude": True})


class PreprocessFallbackPropagationTest(unittest.TestCase):
    def test_preprocess_fallback_propagates_to_meta_and_low_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "sheet.jpg"
            image_path.write_bytes(b"img")

            toolbox = OcrToolbox.__new__(OcrToolbox)
            toolbox.config = PipelineConfig(
                cropper_provider="openrouter",
                cropper_model="crop-model",
                extractor_provider="openrouter",
                extractor_model="extract-model",
            )
            toolbox.validation_engine = ValidationEngine()

            def _ok(step: str, data: dict) -> ToolResult:
                return ToolResult(success=True, run_id="run_fb", step=step, status="completed", data=data)

            toolbox.preprocess_sheet = MethodType(
                lambda self, context, tracer=None: _ok(
                    "preprocess_sheet",
                    {"processed_image": context.input_path, "used_fallback": True},
                ),
                toolbox,
            )
            toolbox.detect_sections = MethodType(
                lambda self, context, image_path, tracer=None: _ok(
                    "detect_sections", {"pixel_boxes": [], "sections": [], "meta": {}}
                ),
                toolbox,
            )
            toolbox.crop_team_fouls = MethodType(
                lambda self, context, tracer=None: _ok(
                    "crop_team_fouls", {"pixel_boxes": [], "sections": [], "meta": {}}
                ),
                toolbox,
            )
            toolbox.enhance_sections = MethodType(
                lambda self, context, tracer=None: _ok("enhance_sections", {"enhanced": []}),
                toolbox,
            )
            toolbox.extract_sections = MethodType(
                lambda self, context, tracer=None: _ok(
                    "extract_sections",
                    {
                        "extracted": {
                            "header": {},
                            "team_a": {"name": "a", "players": []},
                            "team_b": {"name": "b", "players": []},
                            "team_a_fouls": {},
                            "team_b_fouls": {},
                            "progressive_score": {"team_a": [], "team_b": []},
                            "footer": {
                                "final_score": {"team_a": 0, "team_b": 0},
                                "winner": None,
                                "quarters": {
                                    "first": {"team_a": 0, "team_b": 0},
                                    "second": {"team_a": 0, "team_b": 0},
                                    "third": {"team_a": 0, "team_b": 0},
                                    "fourth": {"team_a": 0, "team_b": 0},
                                    "extra": {"team_a": None, "team_b": None},
                                },
                            },
                        },
                        "sections": [],
                    },
                ),
                toolbox,
            )

            res = toolbox.run_full_pipeline(
                image_path,
                runs_dir=Path(tmp) / "runs",
                run_id="run_fb",
                use_run_layout=True,
            )
            final = res.data["result"]
            self.assertTrue(final["meta"].get("preprocess_fallback"))
            self.assertEqual(final["match_status"], "success")
            self.assertEqual(len(final["validation_warnings"]), 1)
            self.assertEqual(final["validation_warnings"][0]["type"], "preprocess_fallback")
            self.assertEqual(final["validation_warnings"][0]["severity"], "low")
            self.assertEqual(final["confidence"]["score"], 0.99)


class ExtractorDefaultsAndHelpersTest(unittest.TestCase):
    def test_pipeline_config_defaults_to_openrouter_and_honors_env(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = PipelineConfig()
        self.assertEqual(cfg.cropper_model, "google/gemini-3-flash-preview")
        self.assertEqual(cfg.extractor_provider, "openrouter")
        self.assertEqual(cfg.extractor_model, "google/gemini-4-carbon")
        self.assertEqual(cfg.extractor_reasoning, {"effort": "low", "exclude": True})

        with mock.patch.dict(os.environ, {}, clear=True):
            opted_out = PipelineConfig(extractor_reasoning=None)
        self.assertIsNone(opted_out.extractor_reasoning)

        with mock.patch.dict(
            os.environ,
            {
                "OCR_DEFAULT_EXTRACTOR_PROVIDER": "gemini",
                "OCR_DEFAULT_EXTRACTOR_MODEL": "gemini-2.5-flash",
            },
            clear=True,
        ):
            env_cfg = PipelineConfig()
        self.assertEqual(env_cfg.extractor_provider, "gemini")
        self.assertEqual(env_cfg.extractor_model, "gemini-2.5-flash")
        self.assertIsNone(env_cfg.extractor_reasoning)

        with mock.patch.dict(
            os.environ,
            {"OCR_DEFAULT_EXTRACTOR_REASONING": '{"effort": "medium", "exclude": false}'},
            clear=True,
        ):
            custom_reasoning_cfg = PipelineConfig()
        self.assertEqual(custom_reasoning_cfg.extractor_reasoning, {"effort": "medium", "exclude": False})

        with mock.patch.dict(os.environ, {"OCR_DEFAULT_EXTRACTOR_REASONING": "off"}, clear=True):
            disabled_reasoning_cfg = PipelineConfig()
        self.assertIsNone(disabled_reasoning_cfg.extractor_reasoning)

        self.assertEqual(parse_reasoning_config("medium"), (True, {"effort": "medium", "exclude": True}))
        with self.assertRaises(ValueError):
            parse_reasoning_config("not-a-valid-effort")

        self.assertEqual(
            build_reasoning_config("none", "openrouter", "google/gemini-3-flash-preview"),
            {"effort": "none", "exclude": True},
        )
        self.assertEqual(
            resolve_default_extractor("docstrange", None),
            ("docstrange", "nanonets-ocr-3"),
        )

    def test_toolbox_wires_default_gemini4_carbon_and_low_reasoning(self) -> None:
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-test-key"}, clear=True):
            cfg = PipelineConfig()
            toolbox = OcrToolbox(cfg)
            extractor = toolbox._build_extractor(cfg)
        self.assertEqual(extractor.provider.model_name, "google/gemini-4-carbon")
        self.assertEqual(extractor.provider.reasoning, {"effort": "low", "exclude": True})

    def test_parse_mark_flag_strict_and_non_strict(self) -> None:
        self.assertTrue(parse_mark_flag("X"))
        self.assertFalse(parse_mark_flag(None, strict=False))
        self.assertFalse(parse_mark_flag("maybe", strict=False))
        with self.assertRaises(TeamMarkdownParseError):
            parse_mark_flag("maybe", strict=True)

    def test_token_usage_from_usage_accepts_provider_usage(self) -> None:
        pu = ProviderUsage(provider="openrouter", model="m", prompt_tokens=3, completion_tokens=4, total_tokens=7)
        tu = TokenUsage.from_usage(pu)
        self.assertEqual((tu.prompt_tokens, tu.completion_tokens, tu.total_tokens), (3, 4, 7))

    def test_build_final_output_normalizes_three_point_alias_and_string_counts(self) -> None:
        built = build_final_output(
            {
                "team_a": {
                    "name": "Alpha",
                    "players": [
                        {
                            "name": "Uno",
                            "number": "4",
                            "points": {"one_point": "1", "two_point": None, "three_point": "2"},
                            "fouls": [],
                            "entered": True,
                            "started": True,
                        }
                    ],
                }
            },
            processing_time_ms=10,
            model="test",
        )
        pts = built["team_a"]["players"][0]["points"]
        self.assertEqual(pts, {"one_point": 1, "two_point": 0, "tree_point": 2})


if __name__ == "__main__":
    unittest.main()
