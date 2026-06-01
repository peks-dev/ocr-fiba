from __future__ import annotations

import re


class TeamMarkdownParseError(ValueError):
    pass


PLAYER_TABLE_HEADER = [
    "nombre",
    "numero",
    "puntos_1",
    "puntos_2",
    "puntos_3",
    "entrada",
    "inicial",
    "faltas",
]

TEAM_NAME_RE = re.compile(r"^-+\s*Nombre del equipo:\s*(.+?)\s*$", re.IGNORECASE)
CAPTAIN_RE = re.compile(r"^-+\s*Entrenador/Cap:\s*(.+?)\s*$", re.IGNORECASE)
PERIOD_RE = re.compile(
    r"^-+\s*Periodo\s*([1-4])\s*:\s*(.+?)\s+faltas\s*$", re.IGNORECASE
)


def parse_team_markdown(content: str) -> dict[str, object]:
    lines = [line.rstrip() for line in content.splitlines()]
    team_name: str | None = None
    captain: str | None = None
    period_values: dict[int, int | None] = {}
    players: list[dict[str, object]] = []

    table_started = False

    team_name_found = False
    captain_found = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if not team_name_found:
            match = TEAM_NAME_RE.match(stripped)
            if match:
                team_name = parse_nullable_text(match.group(1))
                team_name_found = True
                continue

        if not captain_found:
            match = CAPTAIN_RE.match(stripped)
            if match:
                captain = parse_nullable_text(match.group(1))
                captain_found = True
                continue

        match = PERIOD_RE.match(stripped)
        if match:
            period = int(match.group(1))
            period_values[period] = parse_nullable_int(match.group(2))
            continue

        if stripped.startswith("|"):
            row = [cell.strip() for cell in stripped.strip("|").split("|")]
            normalized = [cell.casefold() for cell in row]
            if normalized == PLAYER_TABLE_HEADER:
                table_started = True
                continue
            if is_separator_row(row):
                continue
            if table_started:
                # Stop player parsing if a new table with different column count starts
                if len(row) != len(PLAYER_TABLE_HEADER):
                    table_started = False
                    continue
                if is_placeholder_row(row):
                    continue
                players.append(parse_player_row(row))

    if not team_name_found:
        raise TeamMarkdownParseError("No se encontró 'Nombre del equipo' en el markdown")
    if not captain_found:
        raise TeamMarkdownParseError("No se encontró 'Entrenador/Cap' en el markdown")
    if not table_started:
        raise TeamMarkdownParseError("No se encontró la tabla de jugadores en el markdown")

    team_fouls_quarters = [period_values.get(index) for index in range(1, 5)]
    return {
        "name": team_name,
        "team_fouls_quarters": team_fouls_quarters,
        "captain": captain,
        "players": players,
    }


def parse_player_row(row: list[str]) -> dict[str, object]:
    if len(row) != len(PLAYER_TABLE_HEADER):
        raise TeamMarkdownParseError(
            f"Fila de jugador inválida: se esperaban {len(PLAYER_TABLE_HEADER)} columnas y llegaron {len(row)}"
        )

    fouls = parse_fouls(row[7])
    entered = parse_mark_flag(row[5])
    started = parse_mark_flag(row[6])
    if started:
        entered = True

    return {
        "name": parse_nullable_text(row[0]),
        "number": parse_nullable_int(row[1]),
        "points": {
            "one_point": parse_required_int(row[2]),
            "two_point": parse_required_int(row[3]),
            "tree_point": parse_required_int(row[4]),
        },
        "fouls": fouls,
        "entered": entered,
        "started": started,
    }


def parse_fouls(value: str) -> list[str]:
    text = value.strip()
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_mark_flag(value: str) -> bool:
    normalized = normalize_token(value)
    if normalized in {"", "no", "false", "n", "0", "-", "null", "vacio", "vacío"}:
        return False
    if normalized in {"x", "si", "sí", "true", "s", "1", "yes"}:
        return True
    raise TeamMarkdownParseError(f"Marca booleana no reconocida: {value!r}")


def parse_required_int(value: str) -> int:
    parsed = parse_nullable_int(value)
    if parsed is None:
        # Empty/null cells in scoresheets mean 0 (e.g. no points scored)
        return 0
    return parsed


def parse_nullable_int(value: str) -> int | None:
    text = value.strip()
    normalized = normalize_token(text)
    if normalized in {"", "null", "none", "n/a", "#n/d", "nd"}:
        return None
    try:
        return int(text)
    except ValueError as exc:
        raise TeamMarkdownParseError(f"Entero inválido: {value!r}") from exc


def parse_nullable_text(value: str) -> str | None:
    text = value.strip()
    if normalize_token(text) in {"", "null", "none", "n/a", "#n/d", "nd"}:
        return None
    return text


def is_separator_row(row: list[str]) -> bool:
    return all(set(cell.strip()) <= {"-", ":"} for cell in row)


def is_placeholder_row(row: list[str]) -> bool:
    return row and row[0].strip() == "..."


def normalize_token(value: str) -> str:
    return value.strip().strip(".").casefold()
