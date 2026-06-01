"""
Core validation plugins — extraction consistency checks.

These detect errors introduced by the OCR/extraction process, not errors
in the scoresheet itself. They are always relevant regardless of use case.
"""
from __future__ import annotations

from typing import Any

from ..base import ValidationPlugin, create_warning, CATEGORY_CORE


class QuarterSumsPlugin(ValidationPlugin):
    """Validate that sum of quarters equals final score for both teams."""

    name = "core_quarter_sums"
    description = "Sum of quarter scores must match final score"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        footer = data.get("footer", {})
        quarters = footer.get("quarters", {})
        final_score = footer.get("final_score", {})

        for team in ["team_a", "team_b"]:
            q1 = quarters.get("first", {}).get(team) or 0
            q2 = quarters.get("second", {}).get(team) or 0
            q3 = quarters.get("third", {}).get(team) or 0
            q4 = quarters.get("fourth", {}).get(team) or 0
            extra = quarters.get("extra", {}).get(team) or 0
            final = final_score.get(team) or 0

            total = q1 + q2 + q3 + q4 + extra

            if total != final:
                warnings.append(
                    create_warning(
                        warning_type="quarter_sum_mismatch",
                        severity="high",
                        message=f"Sum of quarters ({total}) does not match final score ({final}) for {team}.",
                        field=f"footer.final_score.{team}",
                        details={"calculated": total, "reported": final, "team": team},
                    )
                )
        return warnings


class DuplicateNumbersPlugin(ValidationPlugin):
    """Validate that there are no duplicate jersey numbers in the same team."""

    name = "core_duplicate_numbers"
    description = "No duplicate jersey numbers within a team"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []

        for team_key in ["team_a", "team_b"]:
            team = data.get(team_key, {})
            players = team.get("players", []) or []

            seen_numbers: dict[str, int] = {}
            for idx, player in enumerate(players):
                number = player.get("number")
                if number is None:
                    continue
                number_str = str(number)
                if number_str in seen_numbers:
                    warnings.append(
                        create_warning(
                            warning_type="duplicate_jersey_number",
                            severity="medium",
                            message=f"Duplicate jersey number {number_str} found in {team_key}.",
                            field=f"{team_key}.players",
                            details={"number": number_str, "team": team_key},
                        )
                    )
                else:
                    seen_numbers[number_str] = idx
        return warnings


class GhostPlayersPlugin(ValidationPlugin):
    """Validate that players who scored appear in the team roster.

    Reports ghost player numbers with full context: which events reference them,
    in which periods, and how many points they account for. This helps consumers
    decide whether to nullify the player_number or investigate further.
    """

    name = "core_ghost_players"
    description = "Scoring players must exist in the team roster"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []

        for team_key in ["team_a", "team_b"]:
            team = data.get(team_key, {})
            players = team.get("players", []) or []
            roster_numbers: set[str] = set()
            for p in players:
                num = p.get("number")
                if num is not None:
                    roster_numbers.add(str(num))

            progressive = data.get("progressive_score", {}).get(team_key, []) or []

            # Group ghost events by player_number for a single consolidated warning
            # Skip None/null player_number — those are handled by ProgressiveVsFinalPlugin
            ghost_events: dict[str, list[dict[str, Any]]] = {}
            for idx, event in enumerate(progressive):
                player_number = event.get("player_number")
                if player_number is None or str(player_number).lower() == "null":
                    continue
                player_number_str = str(player_number)
                if player_number_str not in roster_numbers:
                    ghost_events.setdefault(player_number_str, []).append({
                        "index": idx,
                        "period": event.get("period"),
                        "points": event.get("points") or 0,
                        "running_score": event.get("running_score"),
                    })

            for ghost_num, events in ghost_events.items():
                total_points = sum(e["points"] for e in events)
                periods = sorted(set(e["period"] for e in events if e["period"] is not None))
                event_indices = [e["index"] for e in events]
                warnings.append(
                    create_warning(
                        warning_type="ghost_player",
                        severity="high",
                        message=(
                            f"Player number {ghost_num} scored {total_points} points in "
                            f"{len(events)} event(s) but is not in the roster of {team_key}. "
                            f"Periods: {periods}. Event indices: {event_indices}."
                        ),
                        field=f"progressive_score.{team_key}",
                        details={
                            "player_number": ghost_num,
                            "team": team_key,
                            "event_count": len(events),
                            "total_points": total_points,
                            "periods": periods,
                            "event_indices": event_indices,
                            "events": events,
                        },
                    )
                )
        return warnings


class ProgressiveVsFinalPlugin(ValidationPlugin):
    """Validate that the last running_score matches the final score.

    Provides diagnostic context: whether the progressive score overshoots
    or undershoots the final, and whether ghost players or null player_number
    events may be responsible for the mismatch.
    """

    name = "core_progressive_vs_final"
    description = "Last progressive score must match final score"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        progressive = data.get("progressive_score", {})
        final_scores = data.get("footer", {}).get("final_score", {})

        for team_key in ["team_a", "team_b"]:
            events = progressive.get(team_key, []) or []
            final_score = final_scores.get(team_key) or 0

            if not events:
                continue

            last_event = events[-1]
            last_running_score = last_event.get("running_score")

            if last_running_score is not None and last_running_score != final_score:
                # Diagnose: count ghost and null-player events
                team_data = data.get(team_key, {})
                roster_numbers: set[str] = set()
                for p in (team_data.get("players") or []):
                    num = p.get("number")
                    if num is not None:
                        roster_numbers.add(str(num))

                ghost_count = 0
                null_player_count = 0
                ghost_points = 0
                null_points = 0
                for e in events:
                    pn = e.get("player_number")
                    pts = e.get("points") or 0
                    if pn is None or str(pn).lower() == "null":
                        null_player_count += 1
                        null_points += pts
                    elif str(pn) not in roster_numbers:
                        ghost_count += 1
                        ghost_points += pts

                diff = last_running_score - final_score
                direction = "overshoots" if diff > 0 else "undershoots"

                # Build diagnostic hint
                hints: list[str] = []
                if ghost_count > 0:
                    hints.append(f"{ghost_count} ghost player event(s) accounting for {ghost_points} points")
                if null_player_count > 0:
                    hints.append(f"{null_player_count} event(s) with null player_number accounting for {null_points} points")
                if diff > 0 and ghost_points + null_points >= diff:
                    hints.append("Likely cause: hallucinated events inflate the running score")
                elif diff < 0:
                    hints.append("Likely cause: missing events (progressive score incomplete)")

                message = (
                    f"Last running score ({last_running_score}) {direction} final score "
                    f"({final_score}) by {abs(diff)} for {team_key}."
                )
                if hints:
                    message += " " + "; ".join(hints) + "."

                warnings.append(
                    create_warning(
                        warning_type="progressive_final_mismatch",
                        severity="high",
                        message=message,
                        field=f"progressive_score.{team_key}",
                        details={
                            "last_running_score": last_running_score,
                            "final_score": final_score,
                            "diff": diff,
                            "team": team_key,
                            "ghost_event_count": ghost_count,
                            "ghost_points": ghost_points,
                            "null_player_event_count": null_player_count,
                            "null_points": null_points,
                        },
                    )
                )
        return warnings
