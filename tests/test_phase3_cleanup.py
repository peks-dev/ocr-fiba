"""Tests for Phase 3 cleanup (M3 foul aliases, M7 key resolution, P3 capability)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from ocr_engine_core.output_builder import _normalize_foul_code, _normalize_foul_kind
from ocr_engine_core.utils.image_utils import resolve_provider_api_key, env_names_for_provider


class FoulAliasTest(unittest.TestCase):
    """M3 — consolidated aliases; antideportiva maps to the canonical 'ad'."""

    def test_antideportiva_maps_to_ad_in_code_and_kind(self) -> None:
        # Previously _normalize_foul_code returned 'u' here (inconsistent with
        # the schema and _normalize_foul_kind). Both should now be 'ad'.
        self.assertEqual(_normalize_foul_code("antideportiva"), "ad")
        self.assertEqual(_normalize_foul_kind("ANTIDEPORTIVA"), "ad")
        self.assertEqual(_normalize_foul_code("anti-deportiva"), "ad")

    def test_known_codes_and_empties(self) -> None:
        self.assertEqual(_normalize_foul_code("P2"), "p2")
        self.assertEqual(_normalize_foul_code("personal"), "p")
        self.assertIsNone(_normalize_foul_code("illegible"))
        self.assertIsNone(_normalize_foul_kind("-"))


class ApiKeyResolutionTest(unittest.TestCase):
    """M7 — single source of truth for provider → env var names."""

    def test_gemini_env_precedence(self) -> None:
        self.assertEqual(
            env_names_for_provider("gemini"),
            ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY"),
        )

    def test_resolve_picks_first_available(self) -> None:
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "k2"}, clear=True):
            self.assertEqual(resolve_provider_api_key("gemini"), "k2")

    def test_unknown_provider_falls_back_to_interfaze(self) -> None:
        with mock.patch.dict(os.environ, {"INTERFAZE_API_KEY": "k"}, clear=True):
            self.assertEqual(resolve_provider_api_key("does-not-exist"), "k")


class AgenticCapabilityTest(unittest.TestCase):
    """P3 — capability detection is cached per provider class."""

    def test_docstrange_supports_agentic_openrouter_does_not(self) -> None:
        from ocr_engine_core.extractor import _supports_agentic_mode
        from ocr_engine_core.providers.docstrange import DocstrangeProvider
        from ocr_engine_core.providers.openrouter import OpenrouterProvider

        self.assertTrue(_supports_agentic_mode(DocstrangeProvider))
        self.assertFalse(_supports_agentic_mode(OpenrouterProvider))


if __name__ == "__main__":
    unittest.main()
