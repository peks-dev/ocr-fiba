"""
Base types for the validation plugin system.

Defines the ValidationPlugin protocol that all validation modules must implement,
along with shared helpers for creating warnings and determining match status.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEVERITY_LEVELS = {"low", "medium", "high", "critical"}

MATCH_STATUS = {
    "success": "success",
    "needs_review": "needs_review",
    "error": "error",
}

# Plugin categories — determines grouping and default behavior.
CATEGORY_CORE = "core"            # Extraction consistency — always relevant
CATEGORY_SPORT_RULES = "sport_rules"  # Rules of the sport (e.g. FIBA)
CATEGORY_USE_CASE = "use_case"    # Specific use-case validations


# ---------------------------------------------------------------------------
# Warning helper
# ---------------------------------------------------------------------------

def create_warning(
    warning_type: str,
    severity: str,
    message: str,
    field: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a standardized validation warning."""
    if severity not in SEVERITY_LEVELS:
        severity = "medium"

    warning: dict[str, Any] = {
        "type": warning_type,
        "severity": severity,
        "message": message,
    }
    if field:
        warning["field"] = field
    if details:
        warning["details"] = details
    return warning


# ---------------------------------------------------------------------------
# Match status helper
# ---------------------------------------------------------------------------

def determine_match_status(warnings: list[dict[str, Any]]) -> str:
    """Determine the overall match status based on warning severities."""
    if not warnings:
        return "success"

    has_critical = any(w.get("severity") == "critical" for w in warnings)
    has_high = any(w.get("severity") == "high" for w in warnings)
    has_medium = any(w.get("severity") == "medium" for w in warnings)

    if has_critical:
        return "error"
    if has_high or has_medium:
        return "needs_review"
    return "success"


_SEVERITY_PENALTIES: dict[str, float] = {
    "critical": 0.40,
    "high": 0.20,
    "medium": 0.10,
    "low": 0.03,
}

_SECTION_WEIGHTS: dict[str, float] = {
    "header": 0.10,
    "team_a": 0.25,
    "team_b": 0.25,
    "progressive_score": 0.25,
    "footer": 0.15,
}


def compute_confidence(
    data: dict[str, Any],
    warnings: list[dict[str, Any]],
    match_status: str | None = None,
) -> dict[str, Any]:
    """Compute a deterministic, explainable confidence summary per section and globally."""
    status = match_status or determine_match_status(warnings)
    sections: dict[str, float] = {name: 1.0 for name in _SECTION_WEIGHTS}
    warning_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for w in warnings:
        sev = w.get("severity")
        if sev in warning_counts:
            warning_counts[sev] += 1
        penalty = _SEVERITY_PENALTIES.get(str(sev), 0.10)
        field = str(w.get("field") or "")
        wtype = str(w.get("type") or "")

        primary_section = _section_for_field(field)
        if primary_section in sections:
            sections[primary_section] -= penalty
        else:
            # Global/plugin error penalty spread lightly across sections
            for sec in sections:
                sections[sec] -= penalty * 0.25

        # Cross-section warnings share part of the uncertainty with the coupled section
        details = w.get("details") if isinstance(w.get("details"), dict) else {}
        team = details.get("team")
        if wtype in {"player_progressive_mismatch", "player_shot_breakdown_mismatch"}:
            sections["progressive_score"] -= penalty * 0.5
        elif wtype == "ghost_player" and team in {"team_a", "team_b"}:
            sections[team] -= penalty * 0.5
        elif wtype == "progressive_quarter_mismatch":
            sections["progressive_score"] -= penalty * 0.5

    for sec in sections:
        sections[sec] = round(max(0.0, min(1.0, sections[sec])), 2)

    weighted_score = sum(sections[sec] * weight for sec, weight in _SECTION_WEIGHTS.items())
    if status == "error":
        weighted_score = min(weighted_score, 0.49)
    elif status == "needs_review":
        weighted_score = min(weighted_score, 0.89)
    score = round(max(0.0, min(1.0, weighted_score)), 2)

    if status == "error" or score < 0.70:
        level = "low"
    elif status == "needs_review" or score < 0.90:
        level = "medium"
    else:
        level = "high"

    return {
        "score": score,
        "level": level,
        "sections": sections,
        "warning_counts": warning_counts,
    }


def _section_for_field(field: str) -> str | None:
    for prefix in ("header", "team_a", "team_b", "progressive_score", "footer"):
        if field == prefix or field.startswith(f"{prefix}.") or field.startswith(f"{prefix}["):
            return prefix
    return None


# ---------------------------------------------------------------------------
# ValidationPlugin protocol
# ---------------------------------------------------------------------------

class ValidationPlugin(ABC):
    """
    Base class for validation plugins.

    Every plugin must define:
    - name: unique identifier (used in config to select plugins)
    - description: human-readable description
    - category: one of CATEGORY_CORE, CATEGORY_SPORT_RULES, CATEGORY_USE_CASE
    - validate(data): returns a list of warnings
    """

    name: str
    description: str
    category: str

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Run validations on extracted data. Returns a list of warnings."""
        ...
