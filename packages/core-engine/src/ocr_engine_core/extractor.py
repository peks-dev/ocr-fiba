"""
Core Extractor — Model-agnostic structured extraction from FIBA sections.

This module coordinates the extraction of data from each section image
using a ModelProvider. It handles the special case of team sections
(Markdown output parsed by team_markdown_parser) and accumulates token usage.
"""

from __future__ import annotations

import inspect
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ocr_engine_core.exceptions import ExtractionError, ErrorCode
from ocr_engine_core.utils import parse_mark_flag, parse_team_markdown, TeamMarkdownParseError
from ocr_engine_core.providers.base import TokenUsage
from ocr_engine_core.providers import create_provider, ProviderType
from ocr_engine_core.prompts.extraction import (
    HEADER_PROMPT,
    TEAM_PROMPT,
    TEAM_FOULS_PROMPT,
    PROGRESSIVE_PROMPT,
    FOOTER_PROMPT,
)
from ocr_engine_core.resources.schemas import load_schema

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Extraction target definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExtractionTarget:
    """Defines what to extract from a section image."""
    name: str
    image_name: str
    prompt: str
    schema_name: str | None  # None for Markdown-based extraction
    max_tokens: int


TARGETS = (
    ExtractionTarget("header", "header.png", HEADER_PROMPT, "header", 1200),
    ExtractionTarget("team_a", "team_a.png", TEAM_PROMPT, "team", 4000),
    ExtractionTarget("team_b", "team_b.png", TEAM_PROMPT, "team", 4000),
    ExtractionTarget("team_a_fouls", "team_a_fouls.png", TEAM_FOULS_PROMPT, "team_fouls", 1200),
    ExtractionTarget("team_b_fouls", "team_b_fouls.png", TEAM_FOULS_PROMPT, "team_fouls", 1200),
    ExtractionTarget("progressive_score", "progressive_score.png", PROGRESSIVE_PROMPT, "progressive_score", 6000),
    ExtractionTarget("footer", "footer.png", FOOTER_PROMPT, "footer", 1500),
)


# ---------------------------------------------------------------------------
# Extractor class
# ---------------------------------------------------------------------------

class Extractor:
    """
    Responsible for extracting structured data from section images.
    Uses a ModelProvider for AI calls but handles parsing and coordination.
    """

    def __init__(self, provider, section_providers: dict[str, Any] | None = None,
                 section_max_tokens: dict[str, int] | None = None):
        self.provider = provider
        # Optional per-section provider overrides (section_name → ModelProvider)
        self.section_providers = section_providers or {}
        # Optional per-section max_tokens overrides (section_name → max_tokens)
        self.section_max_tokens = section_max_tokens or {}

    @classmethod
    def from_config(
        cls,
        provider_type: ProviderType,
        model_name: str,
        api_key: str,
        **kwargs,
    ):
        """Factory method to create an Extractor from configuration."""
        provider = create_provider(provider_type, model_name, api_key, **kwargs)
        return cls(provider)

    def extract_all_sections(
        self,
        sections_dir: Path,
        save_raw: bool = False,
        max_workers: int = 7,
    ) -> tuple[dict[str, Any], TokenUsage]:
        """
        Extract data from all section images in the given directory.

        Sections are extracted in parallel using a thread pool, since each
        call is independent and I/O-bound (waiting for the API response).

        Args:
            sections_dir: Directory containing cropped section PNGs.
            save_raw: Whether to include raw API responses.
            max_workers: Maximum number of parallel API calls.

        Returns:
            Tuple of (results_dict, total_token_usage).
        """
        # Validate all section files exist before starting
        for target in TARGETS:
            section_path = sections_dir / target.image_name
            if not section_path.exists():
                raise ExtractionError(
                    f"No existe la sección requerida: {section_path}",
                    code=ErrorCode.EXTRACT_SECTION_MISSING,
                )

        results: dict[str, Any] = {}
        total_usage = TokenUsage()
        started = time.monotonic()

        def _extract_task(target: ExtractionTarget) -> tuple[str, Any, TokenUsage]:
            """Extract a single section — designed for thread pool execution."""
            section_path = sections_dir / target.image_name
            logger.info("Extrayendo %s...", target.name)
            result, usage = self._extract_section(section_path, target)
            logger.info("OK %s", target.name)
            return target.name, result, usage

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_extract_task, target): target
                for target in TARGETS
            }
            for future in as_completed(futures):
                name, result, usage = future.result()
                results[name] = result
                total_usage.add(usage)

        elapsed_ms = int((time.monotonic() - started) * 1000)
        results["_meta"] = {
            "processing_time_ms": elapsed_ms,
            "extractor_model": self.provider.model_name,
            "input_tokens": total_usage.prompt_tokens,
            "output_tokens": total_usage.completion_tokens,
            "total_tokens": total_usage.total_tokens,
        }

        return results, total_usage

    # Providers that prefer JSON output over Markdown for team sections
    JSON_PREFERRED_PROVIDERS = {"docstrange"}

    # Providers/sections that benefit from agentic_mode for consistent output.
    AGENTIC_MODE_SECTIONS: dict[str, set[str]] = {
        "docstrange": {"team_a", "team_b", "progressive_score"},
    }

    def _extract_section(
        self,
        image_path: Path,
        target: ExtractionTarget,
    ) -> tuple[dict[str, Any], TokenUsage]:
        """Extract data from a single section image."""
        # Use section-specific provider if available, otherwise default
        provider = self.section_providers.get(target.name, self.provider)

        # Use section-specific max_tokens if available, otherwise target default
        max_tokens = self.section_max_tokens.get(target.name, target.max_tokens)

        # When using reasoning models, ensure max_tokens is sufficient
        # (reasoning tokens consume most of the budget, leaving little for output)
        if hasattr(provider, 'reasoning') and provider.reasoning:
            if max_tokens < 16000:
                max_tokens = 16000

        # Check if agentic_mode should be enabled for this section
        agentic = target.name in self.AGENTIC_MODE_SECTIONS.get(provider.name, set())

        # Build kwargs for structured_completion — only pass agentic_mode
        # if the provider supports it (DocStrange does, others don't)
        completion_kwargs: dict[str, Any] = {
            "image_path": image_path,
            "prompt": target.prompt,
            "max_tokens": max_tokens,
        }
        if agentic and _supports_agentic_mode(type(provider)):
            completion_kwargs["agentic_mode"] = True

        # Determine whether to use JSON schema or Markdown for this section
        use_json = (
            target.schema_name is not None
            or (target.schema_name is None and provider.name in self.JSON_PREFERRED_PROVIDERS)
        )

        if use_json:
            # Structured extraction with JSON Schema
            schema_name = target.schema_name or "team"
            schema = load_schema(schema_name, provider=provider.name)
            completion_kwargs["schema"] = schema
            result, usage = provider.structured_completion(**completion_kwargs)

            # If provider returned raw_text inside JSON mode, fall through to Markdown parsing
            if isinstance(result, dict) and "raw_text" in result and target.schema_name is None:
                try:
                    parsed = parse_team_markdown(result["raw_text"])
                    return parsed, usage
                except TeamMarkdownParseError:
                    pass  # Fall through to return raw result

            return result, usage
        else:
            # Markdown-based extraction (team sections for providers that prefer it)
            # No schema → provider sends no response_format, allowing free-form Markdown
            completion_kwargs["schema"] = None
            result, usage = provider.structured_completion(**completion_kwargs)

            # If provider returned raw_text, parse it as Markdown
            if isinstance(result, dict) and "raw_text" in result:
                try:
                    parsed = parse_team_markdown(result["raw_text"])
                    return parsed, usage
                except TeamMarkdownParseError as exc:
                    raise ExtractionError(
                        f"No se pudo parsear markdown de {target.name}: {exc}",
                        code=ErrorCode.EXTRACT_MARKDOWN_PARSE,
                    ) from exc

            # If provider returned structured JSON (e.g. Interfaze ignoring Markdown request),
            # try to convert from the Spanish-keyed format to the expected format
            if isinstance(result, dict) and ("equipo" in result or "jugadores" in result):
                return _convert_interfaze_team_json(result), usage

            # If it came back as JSON already, try parsing through markdown parser
            content = json.dumps(result) if not isinstance(result, str) else result
            try:
                parsed = parse_team_markdown(content)
                return parsed, usage
            except TeamMarkdownParseError:
                return result, usage


@lru_cache(maxsize=None)
def _supports_agentic_mode(provider_cls: type) -> bool:
    """Whether a provider's structured_completion accepts agentic_mode.

    Cached per provider class so we don't re-run inspect.signature on every
    section extraction (the hot path runs 7 times per sheet).
    """
    completion = getattr(provider_cls, "structured_completion", None)
    if completion is None:
        return False
    try:
        return "agentic_mode" in inspect.signature(completion).parameters
    except (TypeError, ValueError):
        return False


def _convert_interfaze_team_json(data: dict[str, Any]) -> dict[str, Any]:
    """
    Convert Interfaze's Spanish-keyed team JSON to the expected format.

    Interfaze sometimes ignores the Markdown request and returns structured JSON
    with Spanish keys like 'equipo', 'jugadores', 'nombre_del_equipo', etc.
    This function converts it to the format that output_builder expects.
    """
    equipo = data.get("equipo", {})
    jugadores = data.get("jugadores", [])

    team_name = equipo.get("nombre_del_equipo") if isinstance(equipo, dict) else None
    captain = equipo.get("entrenador_cap") if isinstance(equipo, dict) else None

    players = []
    for j in jugadores:
        if not isinstance(j, dict):
            continue
        fouls_raw = j.get("faltas", "")
        fouls: list[str] = []
        if isinstance(fouls_raw, str) and fouls_raw.strip():
            fouls = [f.strip() for f in fouls_raw.split(",") if f.strip()]
        elif isinstance(fouls_raw, list):
            fouls = [str(f).strip() for f in fouls_raw if str(f).strip()]

        entered_raw = j.get("entrada", "")
        started_raw = j.get("inicial", "")
        entered = parse_mark_flag(entered_raw, strict=False)
        started = parse_mark_flag(started_raw, strict=False)
        if started:
            entered = True

        players.append({
            "name": j.get("nombre"),
            "number": j.get("numero"),
            "points": {
                "one_point": j.get("puntos_1", 0) or 0,
                "two_point": j.get("puntos_2", 0) or 0,
                "tree_point": j.get("puntos_3", 0) or 0,
            },
            "fouls": fouls,
            "entered": entered,
            "started": started,
        })

    return {
        "name": team_name,
        "team_fouls_quarters": [None, None, None, None],  # filled by fouls_override
        "captain": captain,
        "players": players,
    }
