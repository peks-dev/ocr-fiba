"""
Centralized schemas for the FIBA OCR pipeline.

Schemas are stored in canonical format (Interfaze-compatible).
Use load_schema(name, provider) to get the schema adapted for a specific provider.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

SCHEMAS_DIR = Path(__file__).parent

AVAILABLE_SCHEMAS = [
    "cropping",
    "team_fouls_cropping",
    "header",
    "team",
    "team_fouls",
    "progressive_score",
    "footer",
]


def load_schema(name: str, provider: str | None = None) -> dict[str, Any]:
    """
    Load a JSON schema by name, optionally converting for a specific provider.

    Args:
        name: Schema name (without .json extension).
        provider: Provider name ("interfaze" or "gemini"). If None, returns canonical format.

    Returns:
        Schema dict adapted for the specified provider.
    """
    if name not in AVAILABLE_SCHEMAS:
        raise ValueError(f"Schema '{name}' not found. Available: {AVAILABLE_SCHEMAS}")

    path = SCHEMAS_DIR / f"{name}.json"
    with open(path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    if provider == "gemini":
        return _to_gemini_schema(schema)
    return schema


# ---------------------------------------------------------------------------
# Gemini schema conversion
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
    "null": "NULL",
}


def _to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a canonical (Interfaze) JSON schema to Gemini format.

    Key differences:
    - Types in UPPERCASE (STRING, INTEGER, etc.)
    - Union types become arrays of UPPERCASE strings
    - No additionalProperties (Gemini doesn't use it)
    - Add propertyOrdering for deterministic output
    - Remove enum at top-level string types (Gemini handles differently)
    """
    return _convert_node(copy.deepcopy(schema))


def _convert_node(node: Any) -> Any:
    if isinstance(node, dict):
        return _convert_dict(node)
    if isinstance(node, list):
        return [_convert_node(item) for item in node]
    return node


def _convert_dict(d: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    # Handle type field first — may need to extract nullable
    type_value = d.get("type")
    if type_value is not None:
        gemini_type, nullable = _convert_type(type_value)
        result["type"] = gemini_type
        if nullable:
            result["nullable"] = True

    for key, value in d.items():
        if key == "type":
            # Already handled above
            continue
        elif key == "additionalProperties":
            # Gemini doesn't use this; skip
            continue
        elif key == "items":
            result[key] = _convert_node(value)
        elif key == "properties":
            result[key] = _convert_node(value)
            # Add propertyOrdering for deterministic output
            if isinstance(value, dict):
                result["propertyOrdering"] = list(value.keys())
        elif isinstance(value, (dict, list)):
            result[key] = _convert_node(value)
        else:
            result[key] = value

    return result


def _convert_type(type_value: Any) -> tuple[Any, bool]:
    """
    Convert type field from canonical to Gemini format.

    Returns:
        Tuple of (gemini_type, is_nullable).
        Union types like ["string", "null"] become ("STRING", True).
    """
    if isinstance(type_value, str):
        return _TYPE_MAP.get(type_value, type_value), False
    if isinstance(type_value, list):
        # Extract the non-null type and determine nullable
        non_null = [t for t in type_value if t != "null"]
        is_nullable = "null" in type_value
        if len(non_null) == 1:
            return _TYPE_MAP.get(non_null[0], non_null[0]), is_nullable
        elif len(non_null) == 0:
            return "NULL", False
        else:
            # Multiple non-null types — Gemini doesn't support this well
            # Default to the first non-null type
            return _TYPE_MAP.get(non_null[0], non_null[0]), is_nullable
    return type_value, False


__all__ = ["load_schema", "AVAILABLE_SCHEMAS"]
