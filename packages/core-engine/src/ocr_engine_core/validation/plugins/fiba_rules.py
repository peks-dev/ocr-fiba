"""
FIBA rules validation plugins — rules of the sport of basketball.

These check that the extracted data complies with FIBA regulations.
They are relevant for referees and officials but not necessarily for
all consumers of the extraction engine (e.g. a league that just wants
raw stats doesn't need these).
"""
from __future__ import annotations

from typing import Any

from ..base import ValidationPlugin, create_warning, CATEGORY_SPORT_RULES


class PlayerFoulsPlugin(ValidationPlugin):
    """Validate that no player has more than 5 personal fouls (FIBA rule)."""

    name = "fiba_player_fouls"
    description = "No player may exceed 5 personal fouls (FIBA rule)"
    category = CATEGORY_SPORT_RULES

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []

        for team_key in ["team_a", "team_b"]:
            team = data.get(team_key, {})
            players = team.get("players", []) or []

            for idx, player in enumerate(players):
                fouls = player.get("fouls", []) or []
                personal_fouls = [f for f in fouls if isinstance(f, str) and f.upper().startswith("P")]
                total_fouls = len(personal_fouls)

                if total_fouls > 5:
                    name = player.get("name") or f"player_{idx}"
                    warnings.append(
                        create_warning(
                            warning_type="fouls_exceeded",
                            severity="critical",
                            message=f"Player '{name}' has {total_fouls} personal fouls (max allowed is 5).",
                            field=f"{team_key}.players[{idx}].fouls",
                            details={"player": name, "fouls_count": total_fouls, "team": team_key},
                        )
                    )
        return warnings


class TeamFoulsPlugin(ValidationPlugin):
    """Validate that teams do not exceed 4 team fouls per quarter (FIBA rule)."""

    name = "fiba_team_fouls"
    description = "No team may exceed 4 team fouls per quarter (FIBA rule)"
    category = CATEGORY_SPORT_RULES

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []

        for team_key in ["team_a", "team_b"]:
            team = data.get(team_key, {})
            fouls_quarters = team.get("team_fouls_quarters", []) or []

            for quarter_idx, fouls in enumerate(fouls_quarters[:4]):
                if fouls is not None and fouls > 4:
                    warnings.append(
                        create_warning(
                            warning_type="team_fouls_exceeded",
                            severity="low",
                            message=f"{team_key} has {fouls} team fouls in quarter {quarter_idx + 1} (max 4 allowed).",
                            field=f"{team_key}.team_fouls_quarters[{quarter_idx}]",
                            details={"quarter": quarter_idx + 1, "fouls": fouls, "team": team_key},
                        )
                    )
        return warnings
