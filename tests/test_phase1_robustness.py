"""Regression tests for Phase 1 robustness fixes (B2, B3, B4)."""
from __future__ import annotations

import unittest

from ocr_engine_core.output_builder import build_final_output
from ocr_engine_core.providers.base import TokenUsage
from ocr_engine_core.validation.base import determine_match_status


class TokenUsageCoercionTest(unittest.TestCase):
    """B2 — null usage fields must not break token aggregation."""

    def test_none_fields_coerced_to_zero(self) -> None:
        usage = TokenUsage(prompt_tokens=None, completion_tokens=None, total_tokens=None)  # type: ignore[arg-type]
        self.assertEqual(usage.prompt_tokens, 0)
        self.assertEqual(usage.completion_tokens, 0)
        self.assertEqual(usage.total_tokens, 0)

    def test_add_tolerates_none(self) -> None:
        total = TokenUsage()
        # Simulate a provider whose fields slipped through as None post-construction.
        other = TokenUsage()
        other.prompt_tokens = None  # type: ignore[assignment]
        other.total_tokens = None  # type: ignore[assignment]
        total.add(other)  # must not raise TypeError
        self.assertEqual(total.total_tokens, 0)
        self.assertEqual(total.prompt_tokens, 0)


class PeriodReassignmentTest(unittest.TestCase):
    """B3 — string/odd score types must not crash build_final_output."""

    def _events(self) -> dict:
        return {
            "team_a": [{"running_score": "2", "player": "a"}, {"running_score": "5", "player": "a"}],
            "team_b": [],
        }

    def test_string_quarter_scores_do_not_crash(self) -> None:
        results = {
            "progressive_score": self._events(),
            "footer": {
                "quarters": {
                    "first": {"team_a": "10", "team_b": "8"},
                    "second": {"team_a": "12", "team_b": "10"},
                    "third": {"team_a": "9", "team_b": "11"},
                    "fourth": {"team_a": "15", "team_b": "13"},
                }
            },
        }
        out = build_final_output(results, processing_time_ms=1, model="test")
        # Periods get assigned from the coerced cumulative boundaries.
        periods = [e.get("period") for e in out["progressive_score"]["team_a"]]
        self.assertEqual(periods, [1, 1])

    def test_non_numeric_quarter_scores_leave_periods_unassigned(self) -> None:
        results = {
            "progressive_score": self._events(),
            "footer": {
                "quarters": {
                    "first": {"team_a": "n/a", "team_b": "8"},
                    "second": {"team_a": "12", "team_b": "10"},
                    "third": {"team_a": "9", "team_b": "11"},
                    "fourth": {"team_a": "15", "team_b": "13"},
                }
            },
        }
        out = build_final_output(results, processing_time_ms=1, model="test")
        # Points still computed from running_score diffs even without period data.
        points = [e.get("points") for e in out["progressive_score"]["team_a"]]
        self.assertEqual(points, [2, 3])


class MatchStatusTest(unittest.TestCase):
    """B4 — warnings without a 'severity' key must not raise KeyError."""

    def test_missing_severity_does_not_raise(self) -> None:
        warnings = [{"type": "x", "message": "no severity here"}]
        self.assertEqual(determine_match_status(warnings), "success")

    def test_critical_still_detected_with_mixed_warnings(self) -> None:
        warnings = [
            {"type": "x", "message": "no severity"},
            {"type": "y", "severity": "critical", "message": "boom"},
        ]
        self.assertEqual(determine_match_status(warnings), "error")


if __name__ == "__main__":
    unittest.main()
