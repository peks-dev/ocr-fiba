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
    in which periods, and how many points they account for. Also links ghost
    numbers to candidate orphan players in the roster whose table points match.
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

            # Count progressive points per player_number to identify orphan roster players
            prog_points_by_num: dict[str, int] = {}
            for event in progressive:
                pn = event.get("player_number")
                if pn is not None and str(pn).lower() != "null":
                    pn_str = str(pn)
                    prog_points_by_num[pn_str] = prog_points_by_num.get(pn_str, 0) + (event.get("points") or 0)

            orphan_roster_players: list[dict[str, Any]] = []
            for p_idx, p in enumerate(players):
                p_num = p.get("number")
                p_num_str = str(p_num) if p_num is not None else None
                t_pts = _player_table_points(p)
                if t_pts > 0 and (p_num_str is None or prog_points_by_num.get(p_num_str, 0) == 0):
                    orphan_roster_players.append({
                        "index": p_idx,
                        "number": p_num_str,
                        "name": p.get("name"),
                        "table_points": t_pts,
                    })

            # Group ghost events by player_number for a single consolidated warning
            # Skip None/null player_number — those are handled by ProgressiveSequencePlugin
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

                candidates = [
                    c for c in orphan_roster_players
                    if c["table_points"] == total_points
                    or (c["number"] and (c["number"].startswith(ghost_num) or ghost_num.startswith(c["number"])))
                ]

                message = (
                    f"Player number {ghost_num} scored {total_points} points in "
                    f"{len(events)} event(s) but is not in the roster of {team_key}. "
                    f"Periods: {periods}. Event indices: {event_indices}."
                )
                if candidates:
                    cand_desc = ", ".join(
                        f"#{c['number']} ({c['name']}, {c['table_points']} pts in table)"
                        for c in candidates
                    )
                    message += f" Likely roster candidate(s) with 0 progressive points: {cand_desc}."

                details: dict[str, Any] = {
                    "player_number": ghost_num,
                    "team": team_key,
                    "event_count": len(events),
                    "total_points": total_points,
                    "periods": periods,
                    "event_indices": event_indices,
                    "events": events,
                }
                if candidates:
                    details["candidate_roster_players"] = candidates

                warnings.append(
                    create_warning(
                        warning_type="ghost_player",
                        severity="high",
                        message=message,
                        field=f"progressive_score.{team_key}",
                        details=details,
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


def _player_shot_counts(player: dict[str, Any]) -> tuple[int, int, int]:
    points = player.get("points", {}) or {}
    one = points.get("one_point") or 0
    two = points.get("two_point") or 0
    three = points.get("tree_point")
    if three is None:
        three = points.get("three_point") or 0
    return int(one), int(two), int(three)


def _player_table_points(player: dict[str, Any]) -> int:
    one, two, three = _player_shot_counts(player)
    return one + (two * 2) + (three * 3)


class PlayerVsProgressivePlugin(ValidationPlugin):
    """Cross-validate each player's table points and shot breakdown against progressive_score."""

    name = "core_player_vs_progressive"
    description = "Per-player points and shot breakdown must match progressive score events"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        progressive = data.get("progressive_score", {})

        for team_key in ["team_a", "team_b"]:
            team = data.get(team_key, {})
            players = team.get("players", []) or []
            events = progressive.get(team_key, []) or []

            if not players or not events:
                continue

            roster_numbers = {
                str(p.get("number"))
                for p in players
                if p.get("number") is not None
            }

            prog_points: dict[str, int] = {}
            prog_shots: dict[str, dict[int, int]] = {}
            prog_has_unknown_pts: dict[str, bool] = {}
            ghost_points: dict[str, int] = {}

            prev_rs = 0
            for e in events:
                rs = e.get("running_score")
                pts = e.get("points")
                if pts is None and isinstance(rs, int) and 1 <= (rs - prev_rs) <= 3:
                    pts = rs - prev_rs
                if isinstance(rs, int):
                    prev_rs = rs

                pn = e.get("player_number")
                if pn is None or str(pn).lower() == "null":
                    continue
                pn_str = str(pn)

                if isinstance(pts, int) and 1 <= pts <= 3:
                    prog_points[pn_str] = prog_points.get(pn_str, 0) + pts
                    shots = prog_shots.setdefault(pn_str, {1: 0, 2: 0, 3: 0})
                    shots[pts] += 1
                    if pn_str not in roster_numbers:
                        ghost_points[pn_str] = ghost_points.get(pn_str, 0) + pts
                else:
                    prog_has_unknown_pts[pn_str] = True

            for idx, player in enumerate(players):
                num = player.get("number")
                num_str = str(num) if num is not None else None
                name = player.get("name") or f"player_{idx}"
                one, two, three = _player_shot_counts(player)
                table_total = one + (two * 2) + (three * 3)
                prog_total = prog_points.get(num_str, 0) if num_str is not None else 0
                shots = prog_shots.get(num_str, {1: 0, 2: 0, 3: 0}) if num_str is not None else {1: 0, 2: 0, 3: 0}

                if table_total != prog_total:
                    candidate_ghosts = [
                        g_num for g_num, g_pts in ghost_points.items()
                        if prog_total == 0 and g_pts == table_total
                    ]
                    msg = (
                        f"Player #{num_str or '?'} ({name}) in {team_key} has {table_total} points in table "
                        f"(1p:{one}, 2p:{two}, 3p:{three}) but {prog_total} points in progressive_score "
                        f"(1p:{shots[1]}, 2p:{shots[2]}, 3p:{shots[3]})."
                    )
                    if candidate_ghosts:
                        msg += f" Matches ghost player number(s) in progressive_score: {candidate_ghosts}."

                    details: dict[str, Any] = {
                        "team": team_key,
                        "player_index": idx,
                        "player_number": num_str,
                        "player_name": name,
                        "table_points": table_total,
                        "progressive_points": prog_total,
                        "diff": table_total - prog_total,
                        "table_breakdown": {"one_point": one, "two_point": two, "tree_point": three},
                        "progressive_breakdown": {
                            "one_point": shots[1],
                            "two_point": shots[2],
                            "tree_point": shots[3],
                        },
                    }
                    if candidate_ghosts:
                        details["candidate_ghost_numbers"] = candidate_ghosts

                    warnings.append(
                        create_warning(
                            warning_type="player_progressive_mismatch",
                            severity="high",
                            message=msg,
                            field=f"{team_key}.players[{idx}].points",
                            details=details,
                        )
                    )
                elif (
                    table_total > 0
                    and num_str is not None
                    and not prog_has_unknown_pts.get(num_str, False)
                    and (one, two, three) != (shots[1], shots[2], shots[3])
                ):
                    warnings.append(
                        create_warning(
                            warning_type="player_shot_breakdown_mismatch",
                            severity="medium",
                            message=(
                                f"Player #{num_str} ({name}) in {team_key} has matching total points ({table_total}) "
                                f"but shot breakdown differs: table=(1p:{one}, 2p:{two}, 3p:{three}) vs "
                                f"progressive=(1p:{shots[1]}, 2p:{shots[2]}, 3p:{shots[3]})."
                            ),
                            field=f"{team_key}.players[{idx}].points",
                            details={
                                "team": team_key,
                                "player_index": idx,
                                "player_number": num_str,
                                "player_name": name,
                                "total_points": table_total,
                                "table_breakdown": {"one_point": one, "two_point": two, "tree_point": three},
                                "progressive_breakdown": {
                                    "one_point": shots[1],
                                    "two_point": shots[2],
                                    "tree_point": shots[3],
                                },
                            },
                        )
                    )
        return warnings


class ProgressiveSequencePlugin(ValidationPlugin):
    """Validate internal sequence integrity and per-quarter sums in progressive_score."""

    name = "core_progressive_sequence"
    description = "Progressive score must increase monotonically by 1..3 and match quarter scores"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        progressive = data.get("progressive_score", {})
        quarters = data.get("footer", {}).get("quarters", {})
        quarter_names = ["first", "second", "third", "fourth"]

        for team_key in ["team_a", "team_b"]:
            events = progressive.get(team_key, []) or []
            if not events:
                continue

            invalid_jumps: list[dict[str, Any]] = []
            null_players: list[dict[str, Any]] = []
            period_sums: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            all_periods_assigned = True

            prev_rs = 0
            for idx, event in enumerate(events):
                rs = event.get("running_score")
                pts = event.get("points")
                pn = event.get("player_number")
                period = event.get("period")

                if pn is None or str(pn).strip() == "" or str(pn).lower() == "null":
                    null_players.append({"index": idx, "running_score": rs, "period": period})

                if not isinstance(rs, int):
                    invalid_jumps.append({
                        "index": idx,
                        "prev_running_score": prev_rs,
                        "running_score": rs,
                        "diff": None,
                        "stored_points": pts,
                    })
                    continue

                diff = rs - prev_rs
                if diff < 1 or diff > 3 or (pts is not None and pts != diff):
                    invalid_jumps.append({
                        "index": idx,
                        "prev_running_score": prev_rs,
                        "running_score": rs,
                        "diff": diff,
                        "stored_points": pts,
                    })

                actual_pts = pts if isinstance(pts, int) and 1 <= pts <= 3 else (diff if 1 <= diff <= 3 else 0)
                if isinstance(period, int) and period in period_sums:
                    period_sums[period] += actual_pts
                else:
                    all_periods_assigned = False

                prev_rs = rs

            if invalid_jumps:
                warnings.append(
                    create_warning(
                        warning_type="progressive_sequence_jump",
                        severity="high",
                        message=(
                            f"Progressive score for {team_key} has {len(invalid_jumps)} invalid running_score "
                            f"step(s) (must increase by 1, 2, or 3)."
                        ),
                        field=f"progressive_score.{team_key}",
                        details={"team": team_key, "invalid_jumps": invalid_jumps},
                    )
                )

            if null_players:
                warnings.append(
                    create_warning(
                        warning_type="progressive_null_player",
                        severity="medium",
                        message=(
                            f"Progressive score for {team_key} has {len(null_players)} event(s) with "
                            f"null/illegible player_number."
                        ),
                        field=f"progressive_score.{team_key}",
                        details={"team": team_key, "events": null_players},
                    )
                )

            if all_periods_assigned:
                for q_idx, q_name in enumerate(quarter_names, start=1):
                    q_obj = quarters.get(q_name, {})
                    q_score = q_obj.get(team_key) if isinstance(q_obj, dict) else None
                    if isinstance(q_score, int) and period_sums[q_idx] != q_score:
                        warnings.append(
                            create_warning(
                                warning_type="progressive_quarter_mismatch",
                                severity="high",
                                message=(
                                    f"Progressive score points in period {q_idx} ({period_sums[q_idx]}) "
                                    f"do not match footer.quarters.{q_name}.{team_key} ({q_score})."
                                ),
                                field=f"footer.quarters.{q_name}.{team_key}",
                                details={
                                    "team": team_key,
                                    "period": q_idx,
                                    "quarter": q_name,
                                    "progressive_sum": period_sums[q_idx],
                                    "quarter_score": q_score,
                                },
                            )
                        )
        return warnings


class EntryAndFoulsConsistencyPlugin(ValidationPlugin):
    """Validate player entry flags against activity and player fouls against team fouls."""

    name = "core_entry_and_fouls_consistency"
    description = "Player entry marks and foul totals must be consistent with team activity"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        progressive = data.get("progressive_score", {})

        for team_key in ["team_a", "team_b"]:
            team = data.get(team_key, {})
            players = team.get("players", []) or []
            if not players:
                continue

            events = progressive.get(team_key, []) or []
            prog_events_by_num: dict[str, int] = {}
            for e in events:
                pn = e.get("player_number")
                if pn is not None and str(pn).lower() != "null":
                    pn_str = str(pn)
                    prog_events_by_num[pn_str] = prog_events_by_num.get(pn_str, 0) + 1

            countable_player_fouls = 0
            for idx, player in enumerate(players):
                name = player.get("name") or f"player_{idx}"
                num = player.get("number")
                num_str = str(num) if num is not None else None
                entered = player.get("entered")
                started = player.get("started")
                fouls = player.get("fouls") or []
                table_pts = _player_table_points(player)
                prog_cnt = prog_events_by_num.get(num_str, 0) if num_str is not None else 0

                for f in fouls:
                    if not str(f).strip().lower().startswith(("c", "b", "d")):
                        countable_player_fouls += 1

                if started is True and entered is False:
                    warnings.append(
                        create_warning(
                            warning_type="invalid_entry_state",
                            severity="medium",
                            message=f"Player #{num_str or '?'} ({name}) in {team_key} has started=True but entered=False.",
                            field=f"{team_key}.players[{idx}].entered",
                            details={"team": team_key, "player_index": idx, "player_number": num_str},
                        )
                    )
                elif entered is False and (table_pts > 0 or len(fouls) > 0 or prog_cnt > 0):
                    warnings.append(
                        create_warning(
                            warning_type="unentered_player_activity",
                            severity="medium",
                            message=(
                                f"Player #{num_str or '?'} ({name}) in {team_key} is marked entered=False "
                                f"but recorded activity (points={table_pts}, fouls={len(fouls)}, "
                                f"progressive_events={prog_cnt})."
                            ),
                            field=f"{team_key}.players[{idx}].entered",
                            details={
                                "team": team_key,
                                "player_index": idx,
                                "player_number": num_str,
                                "player_name": name,
                                "points": table_pts,
                                "fouls_count": len(fouls),
                                "progressive_events": prog_cnt,
                            },
                        )
                    )

            fouls_quarters = team.get("team_fouls_quarters", []) or []
            numeric_quarters = [q for q in fouls_quarters[:4] if isinstance(q, int)]
            if len(numeric_quarters) == 4:
                team_fouls_sum = sum(numeric_quarters)
                capped_quarters = sum(1 for q in numeric_quarters if q >= 4)
                overflow = countable_player_fouls - team_fouls_sum

                max_expected_overflow = 0 if capped_quarters == 0 else (1 if capped_quarters == 1 else capped_quarters * 2)
                if countable_player_fouls < team_fouls_sum:
                    warnings.append(
                        create_warning(
                            warning_type="team_fouls_mismatch",
                            severity="high",
                            message=(
                                f"Sum of team_fouls_quarters ({team_fouls_sum}) exceeds total player fouls "
                                f"({countable_player_fouls}) for {team_key}."
                            ),
                            field=f"{team_key}.team_fouls_quarters",
                            details={
                                "team": team_key,
                                "team_fouls_quarters": numeric_quarters,
                                "team_fouls_sum": team_fouls_sum,
                                "player_fouls_count": countable_player_fouls,
                            },
                        )
                    )
                elif overflow > max_expected_overflow:
                    sev = "high" if capped_quarters == 0 else "medium"
                    warnings.append(
                        create_warning(
                            warning_type="team_fouls_mismatch",
                            severity=sev,
                            message=(
                                f"Player fouls ({countable_player_fouls}) exceed sum of team_fouls_quarters "
                                f"({team_fouls_sum}, quarters={numeric_quarters}) by {overflow} with only "
                                f"{capped_quarters} quarter(s) at the 4-foul cap for {team_key}."
                            ),
                            field=f"{team_key}.team_fouls_quarters",
                            details={
                                "team": team_key,
                                "team_fouls_quarters": numeric_quarters,
                                "team_fouls_sum": team_fouls_sum,
                                "player_fouls_count": countable_player_fouls,
                                "overflow": overflow,
                                "capped_quarters": capped_quarters,
                            },
                        )
                    )

        return warnings


class IllegibleMarksPlugin(ValidationPlugin):
    """Surface illegible foul/entry cell classifications captured during output normalization."""

    name = "core_illegible_marks"
    description = "Report cells explicitly classified as illegible by the OCR extractor"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        meta = data.get("meta")
        if not isinstance(meta, dict):
            return warnings
        illegible_marks = meta.get("illegible_marks")
        if not isinstance(illegible_marks, list):
            return warnings

        for item in illegible_marks:
            if not isinstance(item, dict):
                continue
            team = item.get("team")
            p_num = item.get("player_number") or "?"
            p_name = item.get("player_name") or "unknown"
            target = item.get("target") or "cell"
            field = item.get("field")
            warnings.append(
                create_warning(
                    warning_type="illegible_mark",
                    severity="medium",
                    message=f"Illegible {target} mark detected for player #{p_num} ({p_name}) in {team}.",
                    field=field,
                    details=dict(item),
                )
            )
        return warnings


class PreprocessFallbackPlugin(ValidationPlugin):
    """Surface preprocess sheet-isolation fallbacks in validation warnings."""

    name = "core_preprocess_fallback"
    description = "Report when sheet isolation fell back to the uncropped original image"
    category = CATEGORY_CORE

    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        meta = data.get("meta")
        if not isinstance(meta, dict) or not meta.get("preprocess_fallback"):
            return []
        return [
            create_warning(
                warning_type="preprocess_fallback",
                severity="low",
                message="Sheet contour isolation fell back to the original image.",
                field=None,
                details={"fallback": "original_image"},
            )
        ]
