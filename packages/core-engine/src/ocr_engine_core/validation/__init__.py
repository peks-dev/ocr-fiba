"""
Validation plugin system for FIBA scoresheet OCR.

Architecture:
- base: ValidationPlugin protocol, warning/status helpers
- registry: Plugin registration and lookup
- engine: ValidationEngine orchestrates plugin execution
- plugins/: Built-in plugins (core, fiba_rules, referee)

Usage:
    from ocr_engine_core.validation import ValidationEngine

    # Default: core plugins only
    engine = ValidationEngine()

    # With specific plugins
    engine = ValidationEngine(plugins=["core_quarter_sums", "fiba_player_fouls"])

    # All plugins
    engine = ValidationEngine(plugins="all")

    # Run
    result = engine.validate(data)

Adding new plugins:
    1. Create a class extending ValidationPlugin in validation/plugins/
    2. Register it in validation/plugins/__init__.py
    3. Use it by name in ValidationEngine(plugins=[...])
"""
from __future__ import annotations

# Auto-register all built-in plugins on import
from . import plugins as _plugins  # noqa: F401

from .base import (
    ValidationPlugin,
    compute_confidence,
    create_warning,
    determine_match_status,
    CATEGORY_CORE,
    CATEGORY_SPORT_RULES,
    CATEGORY_USE_CASE,
)
from .registry import (
    register,
    get,
    get_all,
    get_by_category,
    get_names,
    get_core_names,
    resolve_plugins,
)
from .engine import ValidationEngine

__all__ = [
    "ValidationEngine",
    "ValidationPlugin",
    "compute_confidence",
    "create_warning",
    "determine_match_status",
    "register",
    "get",
    "get_all",
    "get_by_category",
    "get_names",
    "get_core_names",
    "resolve_plugins",
    "CATEGORY_CORE",
    "CATEGORY_SPORT_RULES",
    "CATEGORY_USE_CASE",
]
