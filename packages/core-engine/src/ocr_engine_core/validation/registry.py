"""
Validation Plugin Registry.

Central registry where plugins register themselves. The registry supports:
- Lookup by name or category
- Listing all available plugins
- Auto-discovery of built-in plugins via the plugins package
"""
from __future__ import annotations

from typing import Any

from .base import ValidationPlugin, CATEGORY_CORE


class _Registry:
    """Internal singleton-style registry for validation plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, ValidationPlugin] = {}

    def register(self, plugin: ValidationPlugin) -> None:
        """Register a validation plugin. Overwrites if name already exists."""
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> ValidationPlugin | None:
        """Get a plugin by name, or None if not found."""
        return self._plugins.get(name)

    def get_all(self) -> list[ValidationPlugin]:
        """Get all registered plugins."""
        return list(self._plugins.values())

    def get_by_category(self, category: str) -> list[ValidationPlugin]:
        """Get all plugins in a given category."""
        return [p for p in self._plugins.values() if p.category == category]

    def get_names(self) -> list[str]:
        """Get all registered plugin names."""
        return list(self._plugins.keys())

    def get_core_names(self) -> list[str]:
        """Get names of all core plugins (useful as default)."""
        return [p.name for p in self._plugins.values() if p.category == CATEGORY_CORE]


# Module-level singleton
_registry = _Registry()


def register(plugin: ValidationPlugin) -> None:
    """Register a validation plugin in the global registry."""
    _registry.register(plugin)


def get(name: str) -> ValidationPlugin | None:
    """Get a plugin by name."""
    return _registry.get(name)


def get_all() -> list[ValidationPlugin]:
    """Get all registered plugins."""
    return _registry.get_all()


def get_by_category(category: str) -> list[ValidationPlugin]:
    """Get all plugins in a category."""
    return _registry.get_by_category(category)


def get_names() -> list[str]:
    """Get all registered plugin names."""
    return _registry.get_names()


def get_core_names() -> list[str]:
    """Get names of all core plugins."""
    return _registry.get_core_names()


def resolve_plugins(selection: list[str] | None = None) -> list[ValidationPlugin]:
    """
    Resolve a list of plugin names to plugin instances.

    If selection is None, returns all core plugins (default behavior).
    Raises ValueError if any name is not found in the registry.
    """
    if selection is None:
        names = get_core_names()
    else:
        names = selection

    plugins: list[ValidationPlugin] = []
    missing: list[str] = []
    for name in names:
        plugin = _registry.get(name)
        if plugin is None:
            missing.append(name)
        else:
            plugins.append(plugin)

    if missing:
        available = get_names()
        raise ValueError(
            f"Plugins no encontrados: {', '.join(missing)}. "
            f"Disponibles: {', '.join(available)}"
        )

    return plugins
