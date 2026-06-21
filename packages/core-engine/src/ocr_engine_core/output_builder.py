"""
Output Builder — Normalization and construction of the final JSON result.

This module takes the raw extraction results and builds the final output
with proper structure, defaults, and normalization. Migrated from
extract_sections.py's build_final_output() and normalize_team().
"""

from __future__ import annotations

import unicodedata
from typing import Any


def _strip_diacritics(text: str) -> str:
    """Remove diacritical marks (tildes, accents) from a string, preserving ñ/Ñ.

    e.g. 'martínez' → 'martinez', 'josé' → 'jose', 'ángel' → 'angel'
    but 'muñoz' → 'muñoz', 'peña' → 'peña'
    """
    nfd = unicodedata.normalize("NFD", text)
    chars: list[str] = []
    for i, ch in enumerate(nfd):
        if unicodedata.category(ch) == "Mn":
            # Preserve combining tilde (U+0303) on n/N → ñ/Ñ
            if ch == "\u0303" and chars and chars[-1] in ("n", "N"):
                chars[-1] = unicodedata.normalize("NFC", chars[-1] + ch)
                continue
            continue  # strip all other combining marks
        chars.append(ch)
    return unicodedata.normalize("NFC", "".join(chars))


def _normalize_string(value: str | None) -> str | None:
    """Convert string to lowercase, strip whitespace, and remove diacritics. None stays None."""
    if value is None:
        return None
    if isinstance(value, str):
        return _strip_diacritics(value.lower().strip())
    return value


def _normalize_judge_name(value: str | None) -> str | None:
    """Normalize judge name: lowercase, strip whitespace, remove dots.

    FIBA scoresheets use abbreviated initials like "M. Daniel" or "C. Freddy"
    inconsistently. Stripping dots ensures consistent output regardless of
    whether the model includes them or not.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value.lower().strip().replace(".", "")
    return value


def _reassign_periods_from_footer(
    progressive_score: dict[str, Any],
    footer: dict[str, Any],
) -> dict[str, Any]:
    """Reassign period numbers in progressive_score using footer quarter scores.

    The OCR model does not assign periods — it always returns period: null.
    This function uses the quarter scores from the footer to programmatically
    assign the correct period to each progressive score event.

    Algorithm:
    - Compute cumulative score boundaries from footer quarters.
    - For each event, if running_score <= cumulative_boundary[i], assign period i+1.
    - If footer data is incomplete, periods remain null.

    Returns the progressive_score dict with updated period values.
    """
    quarters = footer.get("quarters", {})

    # Need at least 4 quarter scores to do reassignment
    quarter_names = ["first", "second", "third", "fourth"]
    quarter_scores_a = []
    quarter_scores_b = []
    for qn in quarter_names:
        q = quarters.get(qn, {})
        qa = _coerce_int(q.get("team_a")) if isinstance(q, dict) else None
        qb = _coerce_int(q.get("team_b")) if isinstance(q, dict) else None
        if qa is None or qb is None:
            # Can't reassign without complete (numeric) quarter data — leave periods as-is
            return progressive_score
        quarter_scores_a.append(qa)
        quarter_scores_b.append(qb)

    result = {"team_a": [], "team_b": []}

    for team_key, quarter_scores in [("team_a", quarter_scores_a), ("team_b", quarter_scores_b)]:
        events = progressive_score.get(team_key) or []

        if not events:
            result[team_key] = events
            continue

        # Compute cumulative boundaries
        cumul = 0
        boundaries = []
        for qs in quarter_scores:
            cumul += qs
            boundaries.append(cumul)

        # Reassign periods
        reassigned = []
        for e in events:
            rs = _coerce_int(e.get("running_score"))
            new_event = dict(e)

            if rs is not None:
                assigned = None
                for i, b in enumerate(boundaries):
                    if rs <= b:
                        assigned = i + 1
                        break
                if assigned is None and rs > boundaries[-1]:
                    # Beyond Q4 — extra period(s)
                    assigned = 5
                new_event["period"] = assigned

            reassigned.append(new_event)

        result[team_key] = reassigned

    return result


def _compute_points_from_running_score(
    progressive_score: dict[str, Any],
) -> dict[str, Any]:
    """Compute points for each event from running_score differences.

    The OCR model returns points: null — it only detects which running_scores
    are marked and the player responsible. Points are calculated as:
        points[i] = running_score[i] - running_score[i-1]
    where running_score[-1] = 0 (start of game).

    If running_score is null or the difference is invalid (< 1 or > 3),
    points remains null.

    Returns the progressive_score dict with computed points values.
    """
    result = {"team_a": [], "team_b": []}

    for team_key in ["team_a", "team_b"]:
        events = progressive_score.get(team_key) or []
        prev_rs = 0
        computed = []

        for e in events:
            new_event = dict(e)
            rs = _coerce_int(e.get("running_score"))

            if rs is not None:
                diff = rs - prev_rs
                if 1 <= diff <= 3:
                    new_event["points"] = diff
                # else: leave points as-is (null or whatever OCR set)
                prev_rs = rs

            computed.append(new_event)

        result[team_key] = computed

    return result


def _coerce_int(value: Any) -> int | None:
    """Coerce a score-like value to int, tolerating strings ('21') and floats.

    OCR providers occasionally return numeric fields as strings. Returns None
    when the value cannot be interpreted as a whole number, so callers can skip
    arithmetic instead of crashing the whole run.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        if text.lstrip("-").isdigit():
            return int(text)
    return None


def _normalize_strings_in_obj(obj: Any) -> Any:
    """Recursively normalize all strings in a data structure to lowercase."""
    if isinstance(obj, dict):
        return {k: _normalize_strings_in_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_normalize_strings_in_obj(item) for item in obj]
    elif isinstance(obj, str):
        return _normalize_string(obj)
    else:
        return obj


def build_final_output(
    results: dict[str, Any],
    processing_time_ms: int,
    model: str,
    token_usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Build the final output JSON from extraction results.

    Applies normalization and ensures the output always has the
    expected structure with sensible defaults.

    All string fields are normalized to lowercase for consistent comparison.
    """
    header = _object_result(results, "header")
    team_a = _object_result(results, "team_a")
    team_b = _object_result(results, "team_b")
    team_a_fouls = _object_result(results, "team_a_fouls")
    team_b_fouls = _object_result(results, "team_b_fouls")
    progressive_score = _object_result(results, "progressive_score")
    footer = _object_result(results, "footer")

    # Build normalized progressive_score
    progressive_score_raw = _normalize_strings_in_obj({
        "team_a": progressive_score.get("team_a") or [],
        "team_b": progressive_score.get("team_b") or [],
    })

    # Build normalized footer
    footer_normalized = _normalize_strings_in_obj({
        "final_score": footer.get("final_score")
        or {"team_a": None, "team_b": None},
        "winner": footer.get("winner"),
        "quarters": footer.get("quarters")
        or {
            "first": {"team_a": None, "team_b": None},
            "second": {"team_a": None, "team_b": None},
            "third": {"team_a": None, "team_b": None},
            "fourth": {"team_a": None, "team_b": None},
            "extra": {"team_a": None, "team_b": None},
        },
    })

    # Compute points from running_score differences (OCR returns points: null)
    progressive_score_with_points = _compute_points_from_running_score(
        progressive_score_raw
    )

    # Reassign periods using footer quarter scores when OCR couldn't detect them
    progressive_score_final = _reassign_periods_from_footer(
        progressive_score_with_points, footer_normalized
    )

    return {
        "match_status": None,
        "header": {
            "league": _normalize_string(header.get("league")),
            "tournament": _normalize_string(header.get("tournament")),
            "date": _normalize_string(header.get("date")),
            "time": _normalize_string(header.get("time")),
            "gender": _normalize_string(header.get("gender")),
            "first_judge": _normalize_judge_name(header.get("first_judge")),
            "second_judge": _normalize_judge_name(header.get("second_judge")),
        },
        "team_a": _normalize_team(team_a, fouls_override=team_a_fouls),
        "team_b": _normalize_team(team_b, fouls_override=team_b_fouls),
        "progressive_score": progressive_score_final,
        "footer": footer_normalized,
        "meta": {
            "processing_time_ms": processing_time_ms,
            "extractor_model": model,
            "input_tokens": (token_usage or {}).get("prompt_tokens", 0),
            "output_tokens": (token_usage or {}).get("completion_tokens", 0),
            "total_tokens": (token_usage or {}).get("total_tokens", 0),
        },
        "validation_warnings": [],
    }


def _normalize_team(
    team: dict[str, Any],
    fouls_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize a team result, applying fouls override if available."""
    return {
        "name": _normalize_string(team.get("name")),
        "team_fouls_quarters": _normalize_team_fouls_quarters(
            fouls_override or team
        ),
        "captain": _normalize_string(team.get("captain")),
        "players": _normalize_players(team.get("players") or []),
    }


def _normalize_players(players: Any) -> list[dict[str, Any]]:
    """Normalize player rows while deriving personal fouls from atomic cells."""
    if not isinstance(players, list):
        return []

    normalized_players = []
    for player in players:
        if not isinstance(player, dict):
            continue
        normalized = _normalize_strings_in_obj(player)
        if isinstance(normalized, dict):
            foul_cells = normalized.pop("foul_cells", None)
            if foul_cells is not None:
                normalized["fouls"] = _derive_fouls_from_cells(foul_cells)
            else:
                normalized["fouls"] = _normalize_personal_fouls(normalized.get("fouls"))
            entry_mark = normalized.pop("entry_mark", None)
            entered, started = _derive_entry_flags(
                entry_mark,
                fallback_entered=normalized.get("entered"),
                fallback_started=normalized.get("started"),
            )
            normalized["entered"] = entered
            normalized["started"] = started
            normalized_players.append(normalized)
    return normalized_players


def _derive_entry_flags(
    entry_mark: Any,
    *,
    fallback_entered: Any = None,
    fallback_started: Any = None,
) -> tuple[bool, bool]:
    """Derive public entered/started flags from one visual entry mark state."""
    state: str | None = None
    if isinstance(entry_mark, dict):
        raw_state = entry_mark.get("state")
        if raw_state is not None:
            state = str(raw_state).strip().lower()
    elif entry_mark is not None:
        state = str(entry_mark).strip().lower()

    if state in {"starter", "initial", "inicial", "started"}:
        return True, True
    if state in {"entered", "entry", "entrada", "x"}:
        return True, False
    if state in {"empty", "", "-", "none", "null", "no", "false"}:
        return False, False
    if state in {"illegible", "ilegible"}:
        return False, False

    started = _coerce_bool(fallback_started)
    entered = _coerce_bool(fallback_entered) or started
    return entered, started


def _coerce_bool(value: Any) -> bool:
    """Parse booleans from provider output while defaulting unknown values to False."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized in {"x", "si", "sí", "true", "s", "1", "yes", "entered", "starter", "started"}


def _derive_fouls_from_cells(value: Any) -> list[str]:
    """Derive the public fouls list from per-cell visual classifications."""
    if not isinstance(value, list):
        return []
    return [
        code
        for code in (_normalize_foul_cell(item) for item in value)
        if code is not None
    ]


def _normalize_foul_cell(value: Any) -> str | None:
    """Normalize one atomic foul cell object or legacy string value."""
    if isinstance(value, dict):
        kind = _normalize_foul_kind(value.get("kind"))
        if kind is None:
            return None
        free_throws = value.get("free_throws")
        if free_throws in (1, 2, 3):
            return f"{kind}{free_throws}"
        return kind
    return _normalize_foul_code(value)


def _normalize_personal_fouls(value: Any) -> list[str]:
    """Normalize personal foul codes to the supported FIBA score-sheet tokens.

    This keeps P/P1/P2 detail when the extractor returned it, but removes
    punctuation/spacing/case noise introduced by OCR providers.
    """
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        code = _normalize_foul_code(item)
        if code is not None:
            normalized.append(code)
    return normalized


# Tokens that mean "no foul recorded" — shared by code and kind normalization.
_EMPTY_FOUL_TOKENS = frozenset(
    {"", "-", "empty", "vacia", "vacía", "none", "null", "illegible", "ilegible"}
)

# Human/provider spellings → canonical FIBA single-letter code. "AD"
# (antideportiva) is the canonical code in the bundled schema (team.json) and
# prompts, so both 'antideportiva' and 'anti-deportiva' map to it.
_FOUL_ALIASES = {
    "personal": "p",
    "tecnica": "t",
    "técnica": "t",
    "unsportsmanlike": "u",
    "antideportiva": "ad",
    "anti-deportiva": "ad",
    "disqualifying": "d",
    "descalificante": "d",
    "coach": "c",
    "bench": "b",
}

# Canonical base codes (no free-throw suffix).
_FOUL_BASE_CODES = frozenset({"p", "t", "u", "d", "c", "b", "ad"})


def _foul_token(value: Any) -> str | None:
    """Lowercase/strip a raw foul token and map aliases; None if it means empty."""
    token = str(value).strip().lower().replace(" ", "").replace(".", "")
    if token in _EMPTY_FOUL_TOKENS:
        return None
    return _FOUL_ALIASES.get(token, token)


def _normalize_foul_code(value: Any) -> str | None:
    """Normalize one foul cell/list token, preserving FIBA code detail."""
    if value is None:
        return None
    token = _foul_token(value)
    if token is None:
        return None

    # Match longest-known prefixes first ("ad" before "a"-less single letters).
    allowed_prefixes = ("ad", "p", "t", "u", "d", "c", "b")
    prefix = next((candidate for candidate in allowed_prefixes if token.startswith(candidate)), None)
    if prefix is None:
        return token
    suffix = token[len(prefix):]
    if suffix in {"", "1", "2", "3"}:
        return prefix + suffix
    # Keep the safest known family when OCR adds stray characters.
    return prefix


def _normalize_foul_kind(value: Any) -> str | None:
    """Normalize a base foul kind from object-style foul_cells."""
    if value is None:
        return None
    token = _foul_token(value)
    if token is None:
        return None
    if token in _FOUL_BASE_CODES:
        return token
    return _normalize_foul_code(token)


def _normalize_team_fouls_quarters(source: dict[str, Any]) -> list[int | None]:
    """Normalize team fouls to exactly 4 quarter values.

    Supports three input formats:
    1. Flat array: {"team_fouls_quarters": [0, 1, 1, 1]}
    2. Structured (faltas): {"faltas_de_equipo": [{"periodo": 1, "total_faltas": 0}, ...]}
    3. Structured (periodos): {"periodos": [{"cuarto": 1, "casillas": [...], "total_faltas": 3}, ...]}
    """
    # Try periodos format first (most detailed)
    periodos = source.get("periodos")
    if isinstance(periodos, list) and periodos and isinstance(periodos[0], dict):
        quarters: list[int | None] = [None, None, None, None]
        for entry in periodos:
            if not isinstance(entry, dict):
                continue
            cuarto = entry.get("cuarto")
            total = entry.get("total_faltas")
            if isinstance(cuarto, int) and 1 <= cuarto <= 4:
                idx = cuarto - 1
                # Prefer total_faltas; fall back to counting X in casillas
                if isinstance(total, int):
                    quarters[idx] = total
                else:
                    casillas = entry.get("casillas")
                    if isinstance(casillas, list):
                        quarters[idx] = sum(1 for c in casillas if isinstance(c, str) and c.upper() == "X")
        return quarters

    # Try faltas_de_equipo format
    faltas = source.get("faltas_de_equipo")
    if isinstance(faltas, list) and faltas and isinstance(faltas[0], dict):
        quarters = [None, None, None, None]
        for entry in faltas:
            if not isinstance(entry, dict):
                continue
            periodo = entry.get("periodo")
            total = entry.get("total_faltas")
            if isinstance(periodo, int) and 1 <= periodo <= 4:
                idx = periodo - 1
                if isinstance(total, int) or total is None:
                    quarters[idx] = total
        return quarters

    # Fall back to flat array format
    value = source.get("team_fouls_quarters")
    if not isinstance(value, list):
        return [None, None, None, None]
    quarters = []
    for item in value[:4]:
        if isinstance(item, int) or item is None:
            quarters.append(item)
        else:
            quarters.append(None)
    while len(quarters) < 4:
        quarters.append(None)
    return quarters


def _object_result(results: dict[str, Any], name: str) -> dict[str, Any]:
    """Safely extract a dict result from the results map."""
    value = results.get(name)
    if isinstance(value, dict):
        return value
    return {}
