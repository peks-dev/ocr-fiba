"""
Referee use-case validation plugins — checks useful for officials
verifying the accuracy of a scoresheet.

These go beyond extraction consistency and sport rules: they cross-reference
multiple sections to verify the acta was filled correctly. Useful for
referees completing or reviewing a scoresheet, but not needed by consumers
who just want raw stats.
"""
from __future__ import annotations

from typing import Any

from ..base import ValidationPlugin, create_warning, CATEGORY_CORE, CATEGORY_USE_CASE


class PlayerPointsSumPlugin(ValidationPlugin):
    """Validate that sum of individual player points equals team final score."""

    name = "referee_player_points_sum"
    description = "Sum of player points must match team final score"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        final_scores = data.get("footer", {}).get("final_score", {})

        for team_key in ["team_a", "team_b"]:
            team = data.get(team_key, {})
            players = team.get("players", []) or []
            final_score = final_scores.get(team_key) or 0

            total_points = 0
            for player in players:
                points = player.get("points", {}) or {}
                one = points.get("one_point") or 0
                two = points.get("two_point") or 0
                three = points.get("tree_point")
                if three is None:
                    three = points.get("three_point") or 0
                total_points += (one * 1) + (two * 2) + (three * 3)

            if total_points != final_score:
                warnings.append(
                    create_warning(
                        warning_type="player_points_mismatch",
                        severity="high",
                        message=f"Sum of player points ({total_points}) does not match final score ({final_score}) for {team_key}.",
                        field=f"{team_key}.players",
                        details={"calculated": total_points, "reported": final_score, "team": team_key},
                    )
                )
        return warnings


class WinnerConsistencyPlugin(ValidationPlugin):
    """Validate that the declared winner has the higher final score."""

    name = "referee_winner_consistency"
    description = "Declared winner must have the higher score"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        footer = data.get("footer", {})
        winner = footer.get("winner")
        final_score = footer.get("final_score", {})

        if not winner:
            return warnings

        score_a = final_score.get("team_a") or 0
        score_b = final_score.get("team_b") or 0

        # Try to match winner against team names
        team_a_name = data.get("team_a", {}).get("name")
        team_b_name = data.get("team_b", {}).get("name")

        winner_lower = winner.lower()

        # Determine which team the winner refers to
        winner_is_a = (
            winner_lower in ["team_a", "a"]
            or (team_a_name and winner_lower == team_a_name.lower())
        )
        winner_is_b = (
            winner_lower in ["team_b", "b"]
            or (team_b_name and winner_lower == team_b_name.lower())
        )

        if winner_is_a and score_a <= score_b:
            warnings.append(
                create_warning(
                    warning_type="winner_inconsistency",
                    severity="medium",
                    message=f"Winner declared as team_a ({team_a_name}) but team_b has equal or higher score ({score_a} vs {score_b}).",
                    field="footer.winner",
                    details={"winner": winner, "score_a": score_a, "score_b": score_b},
                )
            )
        elif winner_is_b and score_b <= score_a:
            warnings.append(
                create_warning(
                    warning_type="winner_inconsistency",
                    severity="medium",
                    message=f"Winner declared as team_b ({team_b_name}) but team_a has equal or higher score ({score_a} vs {score_b}).",
                    field="footer.winner",
                    details={"winner": winner, "score_a": score_a, "score_b": score_b},
                )
            )
        return warnings
