"""Unit tests for Phase 1 validation plugins, illegible mark propagation, and confidence scoring."""
from __future__ import annotations

import unittest

from ocr_engine_core.output_builder import build_final_output
from ocr_engine_core.validation import ValidationEngine, compute_confidence, determine_match_status


class ValidationAndConfidenceTest(unittest.TestCase):
    def test_medium_warning_sets_needs_review_and_caps_confidence(self) -> None:
        warnings = [
            {
                "type": "duplicate_jersey_number",
                "severity": "medium",
                "message": "Duplicate #4",
                "field": "team_a.players",
            }
        ]
        status = determine_match_status(warnings)
        self.assertEqual(status, "needs_review")
        conf = compute_confidence({}, warnings, match_status=status)
        self.assertEqual(conf["level"], "medium")
        self.assertLessEqual(conf["score"], 0.89)
        self.assertEqual(conf["sections"]["team_a"], 0.9)

    def test_player_vs_progressive_detects_total_and_shot_breakdown_mismatch(self) -> None:
        data = {
            "team_a": {
                "name": "alpha",
                "team_fouls_quarters": [1, 0, 0, 0],
                "players": [
                    {
                        "name": "player one",
                        "number": "4",
                        "points": {"one_point": 0, "two_point": 0, "tree_point": 1},  # 3 pts (1x3p)
                        "fouls": ["p"],
                        "entered": True,
                        "started": True,
                    },
                    {
                        "name": "player two",
                        "number": "8",
                        "points": {"one_point": 1, "two_point": 1, "tree_point": 0},  # 3 pts (1x1p, 1x2p)
                        "fouls": [],
                        "entered": True,
                        "started": True,
                    },
                ],
            },
            "team_b": {"name": "beta", "team_fouls_quarters": [0, 0, 0, 0], "players": []},
            "progressive_score": {
                "team_a": [
                    # Player #4 only has 2 pts in progressive (mismatch in total: 3 vs 2)
                    {"player_number": "4", "running_score": 2, "points": 2, "period": 1},
                    # Player #8 has 3 pts in progressive via a 3-pointer (mismatch in breakdown: 1p+2p vs 3p)
                    {"player_number": "8", "running_score": 5, "points": 3, "period": 1},
                ],
                "team_b": [],
            },
            "footer": {
                "final_score": {"team_a": 5, "team_b": 0},
                "winner": "alpha",
                "quarters": {
                    "first": {"team_a": 5, "team_b": 0},
                    "second": {"team_a": 0, "team_b": 0},
                    "third": {"team_a": 0, "team_b": 0},
                    "fourth": {"team_a": 0, "team_b": 0},
                    "extra": {"team_a": None, "team_b": None},
                },
            },
        }
        engine = ValidationEngine(plugins=["core_player_vs_progressive"])
        validated = engine.validate(data)
        types = [w["type"] for w in validated["validation_warnings"]]
        self.assertIn("player_progressive_mismatch", types)
        self.assertIn("player_shot_breakdown_mismatch", types)

    def test_ghost_player_links_orphan_roster_candidate(self) -> None:
        data = {
            "team_a": {
                "name": "alpha",
                "team_fouls_quarters": [0, 0, 0, 0],
                "players": [
                    {
                        "name": "gongora cesar",
                        "number": "60",
                        "points": {"one_point": 0, "two_point": 3, "tree_point": 0},
                        "fouls": [],
                        "entered": True,
                        "started": True,
                    }
                ],
            },
            "team_b": {"name": "beta", "team_fouls_quarters": [0, 0, 0, 0], "players": []},
            "progressive_score": {
                "team_a": [
                    {"player_number": "6", "running_score": 2, "points": 2, "period": 1},
                    {"player_number": "6", "running_score": 4, "points": 2, "period": 1},
                    {"player_number": "6", "running_score": 6, "points": 2, "period": 2},
                ],
                "team_b": [],
            },
            "footer": {"final_score": {"team_a": 6, "team_b": 0}, "quarters": {}},
        }
        engine = ValidationEngine(plugins=["core_ghost_players", "core_player_vs_progressive"])
        validated = engine.validate(data)
        by_type = {w["type"]: w for w in validated["validation_warnings"]}
        self.assertIn("ghost_player", by_type)
        self.assertEqual(
            by_type["ghost_player"]["details"]["candidate_roster_players"][0]["number"],
            "60",
        )
        self.assertIn("player_progressive_mismatch", by_type)
        self.assertEqual(
            by_type["player_progressive_mismatch"]["details"]["candidate_ghost_numbers"],
            ["6"],
        )

    def test_progressive_sequence_detects_jumps_null_player_and_quarter_mismatch(self) -> None:
        data = {
            "team_a": {"players": []},
            "team_b": {"players": []},
            "progressive_score": {
                "team_a": [
                    {"player_number": None, "running_score": 2, "points": 2, "period": 1},
                    {"player_number": "4", "running_score": 7, "points": None, "period": 1},
                ],
                "team_b": [],
            },
            "footer": {
                "final_score": {"team_a": 7, "team_b": 0},
                "quarters": {
                    "first": {"team_a": 7, "team_b": 0},
                    "second": {"team_a": 0, "team_b": 0},
                    "third": {"team_a": 0, "team_b": 0},
                    "fourth": {"team_a": 0, "team_b": 0},
                },
            },
        }
        engine = ValidationEngine(plugins=["core_progressive_sequence"])
        validated = engine.validate(data)
        types = {w["type"] for w in validated["validation_warnings"]}
        self.assertIn("progressive_sequence_jump", types)
        self.assertIn("progressive_null_player", types)
        self.assertIn("progressive_quarter_mismatch", types)

    def test_entry_and_fouls_consistency_detects_unentered_activity_and_foul_mismatch(self) -> None:
        data = {
            "team_a": {
                "players": [
                    {
                        "name": "active bench",
                        "number": "10",
                        "points": {"one_point": 2, "two_point": 0, "tree_point": 0},
                        "fouls": ["p1", "p2", "p", "p"],
                        "entered": False,
                        "started": False,
                    }
                ],
                "team_fouls_quarters": [1, 1, 0, 0],
            },
            "team_b": {"players": [], "team_fouls_quarters": [0, 0, 0, 0]},
            "progressive_score": {"team_a": [], "team_b": []},
        }
        engine = ValidationEngine(plugins=["core_entry_and_fouls_consistency"])
        validated = engine.validate(data)
        types = {w["type"] for w in validated["validation_warnings"]}
        self.assertIn("unentered_player_activity", types)
        self.assertIn("team_fouls_mismatch", types)

    def test_illegible_marks_propagated_from_output_builder_to_validation_warnings(self) -> None:
        raw_results = {
            "header": {},
            "team_a": {
                "name": "alpha",
                "players": [
                    {
                        "name": "perez juan",
                        "number": "5",
                        "points": {"one_point": 0, "two_point": 0, "tree_point": 0},
                        "foul_cells": [
                            {"kind": "P", "free_throws": 2},
                            {"kind": "illegible", "free_throws": None},
                            {"kind": "empty", "free_throws": None},
                            {"kind": "empty", "free_throws": None},
                            {"kind": "empty", "free_throws": None},
                        ],
                        "entry_mark": {"state": "illegible"},
                    }
                ],
            },
            "team_b": {},
            "progressive_score": {},
            "footer": {},
        }
        built = build_final_output(raw_results, processing_time_ms=10, model="test-model")
        self.assertEqual(len(built["meta"]["illegible_marks"]), 2)

        engine = ValidationEngine(plugins=["core_illegible_marks"])
        validated = engine.validate(built)
        warnings = validated["validation_warnings"]
        self.assertEqual(len(warnings), 2)
        self.assertTrue(all(w["type"] == "illegible_mark" for w in warnings))
        self.assertEqual(validated["match_status"], "needs_review")


if __name__ == "__main__":
    unittest.main()
