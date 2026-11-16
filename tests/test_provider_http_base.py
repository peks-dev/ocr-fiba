"""Tests for the shared HttpJsonProvider base: retry/backoff and parsing."""
from __future__ import annotations

import unittest
from pathlib import Path

from ocr_engine_core.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServerError,
)
from ocr_engine_core.providers.http_base import HttpJsonProvider
from ocr_engine_core.providers.base import TokenUsage


class _StubProvider(HttpJsonProvider):
    """Minimal concrete provider that records request attempts."""

    name = "stub"
    ENDPOINT = "https://example.test/v1"

    def __init__(self) -> None:
        super().__init__("stub-model", "stub-key")
        self.attempts = 0
        self.script: list = []  # each item: an Exception to raise or a dict to return

    def _post_once(self, url, payload, headers, context):  # noqa: ANN001
        self.attempts += 1
        action = self.script[self.attempts - 1]
        if isinstance(action, Exception):
            raise action
        return action

    def _sleep_backoff(self, attempt: int) -> None:  # avoid real sleeping in tests
        return None

    def _call_api(self, image_path, prompt, schema=None, max_tokens=4000):  # noqa: ANN001
        body = self._make_request({}, "ctx")
        return self._parse_json_or_raw(body["content"]), self._extract_openai_usage(body)


class RetryPolicyTest(unittest.TestCase):
    def _provider(self, script: list) -> _StubProvider:
        provider = _StubProvider()
        provider.script = script
        return provider

    def test_retries_then_succeeds_on_rate_limit(self) -> None:
        provider = self._provider([
            ProviderRateLimitError("429", provider="stub"),
            ProviderServerError("503", provider="stub"),
            {"ok": True},
        ])
        result = provider._make_request({}, "ctx")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(provider.attempts, 3)

    def test_gives_up_after_max_attempts(self) -> None:
        provider = self._provider([ProviderRateLimitError("429", provider="stub")] * 10)
        with self.assertRaises(ProviderRateLimitError):
            provider._make_request({}, "ctx")
        self.assertEqual(provider.attempts, HttpJsonProvider.MAX_ATTEMPTS)

    def test_non_retryable_error_is_not_retried(self) -> None:
        provider = self._provider([ProviderAuthError("401", provider="stub"), {"ok": True}])
        with self.assertRaises(ProviderAuthError):
            provider._make_request({}, "ctx")
        self.assertEqual(provider.attempts, 1)


class ParsingHelpersTest(unittest.TestCase):
    def test_strip_code_fences(self) -> None:
        fenced = "```json\n{\"a\": 1}\n```"
        self.assertEqual(HttpJsonProvider._strip_code_fences(fenced), '{"a": 1}')

    def test_parse_json_or_raw_falls_back(self) -> None:
        provider = _StubProvider()
        self.assertEqual(provider._parse_json_or_raw("not json"), {"raw_text": "not json"})
        self.assertEqual(provider._parse_json_or_raw('{"a": 1}'), {"a": 1})

    def test_extract_openai_usage_handles_null_fields(self) -> None:
        provider = _StubProvider()
        usage = provider._extract_openai_usage(
            {"usage": {"prompt_tokens": None, "completion_tokens": 5, "total_tokens": None}}
        )
        self.assertIsInstance(usage, TokenUsage)
        self.assertEqual(usage.prompt_tokens, 0)
        self.assertEqual(usage.completion_tokens, 5)

    def test_parse_boxes_single_object_form(self) -> None:
        boxes = HttpJsonProvider._parse_boxes(
            {"name": "header", "x_min": 0, "y_min": 0, "x_max": 10, "y_max": 5}
        )
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].name, "header")

    def test_parse_boxes_skips_invalid_entries(self) -> None:
        boxes = HttpJsonProvider._parse_boxes(
            {"sections": [{"name": "h", "x_min": 0, "y_min": 0, "x_max": 1, "y_max": 1}, {"bad": 1}]}
        )
        self.assertEqual(len(boxes), 1)


if __name__ == "__main__":
    unittest.main()
