"""
Validation Engine — orchestrates plugin execution and determines match status.

The engine takes a list of ValidationPlugin instances, runs them against
the extracted data, and produces the final validation result.
"""
from __future__ import annotations

from typing import Any

from .base import ValidationPlugin, compute_confidence, create_warning, determine_match_status
from .registry import resolve_plugins


class ValidationEngine:
    """
    Runs selected validation plugins against extracted data.

    Usage:
        # Default: core plugins only
        engine = ValidationEngine()

        # Specific plugins
        engine = ValidationEngine(plugins=["core_quarter_sums", "fiba_player_fouls"])

        # All plugins
        engine = ValidationEngine(plugins="all")

        # Run
        result = engine.validate(data)
    """

    def __init__(self, plugins: list[str] | str | None = None) -> None:
        """
        Args:
            plugins: List of plugin names, "all" for every registered plugin,
                    or None for core plugins only (default).
        """
        if plugins == "all":
            from .registry import get_all
            self._plugins: list[ValidationPlugin] = get_all()
        elif isinstance(plugins, list):
            self._plugins = resolve_plugins(plugins)
        else:
            # None = core only
            self._plugins = resolve_plugins(None)

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Run all selected plugins against the data.

        Adds 'validation_warnings' and 'match_status' to the data dict.
        Each warning includes a 'plugin' field indicating which plugin produced it.
        """
        all_warnings: list[dict[str, Any]] = []

        for plugin in self._plugins:
            try:
                warnings = plugin.validate(data)
                # Tag each warning with the plugin that produced it
                for w in warnings:
                    w["plugin"] = plugin.name
                all_warnings.extend(warnings)
            except Exception as exc:
                # A plugin crashing shouldn't break the whole pipeline
                all_warnings.append(
                    create_warning(
                        warning_type="plugin_error",
                        severity="medium",
                        message=f"Plugin '{plugin.name}' failed: {exc}",
                        field=None,
                        details={"plugin": plugin.name, "error": str(exc)},
                    )
                )

        match_status = determine_match_status(all_warnings)

        data["validation_warnings"] = all_warnings
        data["match_status"] = match_status
        data["confidence"] = compute_confidence(data, all_warnings, match_status=match_status)

        return data

    @property
    def active_plugins(self) -> list[str]:
        """Names of currently active plugins."""
        return [p.name for p in self._plugins]
