"""
Footer Markdown parser — converts free-form Markdown from the LLM
into the structured dict that the pipeline expects (matching footer.json schema).
"""
from __future__ import annotations

import re


class FooterMarkdownParseError(ValueError):
    pass


# Regex patterns for the Markdown sections
SCORE_A_RE = re.compile(r"^-?\s*Equipo\s*A\s*:\s*(.+)", re.IGNORECASE)
SCORE_B_RE = re.compile(r"^-?\s*Equipo\s*B\s*:\s*(.+)", re.IGNORECASE)
WINNER_RE = re.compile(r"^-\s*(.+)$")


def parse_footer_markdown(content: str) -> dict[str, object]:
    """
    Parse the Markdown response from the footer extraction prompt
    into the structured dict matching the footer schema.

    Expected Markdown format:
    ## Marcador final
    - Equipo A: 40
    - Equipo B: 56

    ## Equipo ganador
    - QUETZALES PRIME

    ## Puntos por periodo
    | periodo | equipo_A | equipo_B |
    |---|---|---|
    | 1 | 11 | 17 |
    | 2 | 10 | 9 |
    | 3 | 8 | 17 |
    | 4 | 11 | 13 |
    | extra | | |
    """
    lines = [line.rstrip() for line in content.splitlines()]

    final_score_a: int | None = None
    final_score_b: int | None = None
    winner: str | None = None
    quarters: dict[str, dict[str, int | None]] = {
        "first": {"team_a": None, "team_b": None},
        "second": {"team_a": None, "team_b": None},
        "third": {"team_a": None, "team_b": None},
        "fourth": {"team_a": None, "team_b": None},
        "extra": {"team_a": None, "team_b": None},
    }

    current_section: str | None = None
    table_started = False
    period_order = ["first", "second", "third", "fourth", "extra"]
    period_rows: list[tuple[str, int | None, int | None]] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect section headers
        if stripped.startswith("##"):
            header_text = stripped.lstrip("#").strip().casefold()
            if "marcador" in header_text:
                current_section = "score"
            elif "ganador" in header_text:
                current_section = "winner"
            elif "periodo" in header_text or "puntos" in header_text:
                current_section = "periods"
            continue

        # Parse score section
        if current_section == "score":
            match_a = SCORE_A_RE.match(stripped)
            if match_a:
                final_score_a = _parse_int_or_null(match_a.group(1))
                continue
            match_b = SCORE_B_RE.match(stripped)
            if match_b:
                final_score_b = _parse_int_or_null(match_b.group(1))
                continue

        # Parse winner section
        if current_section == "winner":
            match = WINNER_RE.match(stripped)
            if match:
                winner = _parse_text_or_null(match.group(1))
                continue

        # Parse periods table
        if current_section == "periods":
            if stripped.startswith("|"):
                row = [cell.strip() for cell in stripped.strip("|").split("|")]
                # Skip header row and separator row
                if _is_table_header(row) or _is_separator(row):
                    table_started = True
                    continue
                if table_started or len(row) >= 3:
                    period_name, val_a, val_b = row[0], row[1], row[2]
                    period_key = _map_period(period_name)
                    if period_key is not None:
                        period_rows.append((period_key, _parse_int_or_null(val_a), _parse_int_or_null(val_b)))

    # Fill quarters from parsed rows
    for period_key, val_a, val_b in period_rows:
        if period_key in quarters:
            quarters[period_key]["team_a"] = val_a
            quarters[period_key]["team_b"] = val_b

    return {
        "final_score": {
            "team_a": final_score_a,
            "team_b": final_score_b,
        },
        "winner": winner,
        "quarters": quarters,
    }


def _map_period(name: str) -> str | None:
    """Map a period name from markdown to the schema key."""
    normalized = name.strip().casefold()
    mapping = {
        "1": "first",
        "2": "second",
        "3": "third",
        "4": "fourth",
        "extra": "extra",
        "prórroga": "extra",
        "prorroga": "extra",
        "overtime": "extra",
        "periodo 1": "first",
        "periodo 2": "second",
        "periodo 3": "third",
        "periodo 4": "fourth",
        "periodo extra": "extra",
        "1er": "first",
        "2do": "second",
        "3er": "third",
        "4to": "fourth",
    }
    # Try exact match first
    if normalized in mapping:
        return mapping[normalized]
    # Try prefix match
    for key, value in mapping.items():
        if normalized.startswith(key):
            return value
    return None


def _parse_int_or_null(value: str) -> int | None:
    """Parse an integer or return None for empty/null markers."""
    text = value.strip()
    if text.casefold() in {"", "null", "none", "n/a", "-", "vacío", "vacio", "–", "—"}:
        return None
    # Try to extract a number from the text (handles cases like "08" or "8.")
    digits = re.search(r"\d+", text)
    if digits:
        return int(digits.group())
    return None


def _parse_text_or_null(value: str) -> str | None:
    """Parse text or return None for empty/null markers."""
    text = value.strip()
    if text.casefold() in {"", "null", "none", "n/a", "-", "vacío", "vacio"}:
        return None
    return text


def _is_table_header(row: list[str]) -> bool:
    """Check if the row is a table header (contains 'periodo' or 'equipo')."""
    normalized = [cell.casefold() for cell in row]
    return any("periodo" in cell or "equipo" in cell for cell in normalized)


def _is_separator(row: list[str]) -> bool:
    """Check if the row is a markdown table separator."""
    return all(set(cell.strip()) <= {"-", ":"} for cell in row)
