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

    if has_critical:
        return "error"
    if has_high:
        return "needs_review"
    return "success"


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
