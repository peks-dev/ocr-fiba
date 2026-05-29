"""
Pipeline configuration for model selection per phase.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from providers import ProviderType


@dataclass
class SectionOverride:
    """Override the default extractor for a specific section."""
    provider: ProviderType
    model: str
    reasoning: dict[str, Any] | None = None
    max_tokens: int | None = None


@dataclass
class PipelineConfig:
    """
    Configuration object that defines which model/provider to use
    for each phase of the OCR pipeline.
    """

    # === Cropping Phase ===
    cropper_provider: ProviderType = "openrouter"
    cropper_model: str = "google/gemini-3-flash-preview"

    # === Extraction Phase ===
    extractor_provider: ProviderType = "docstrange"
    extractor_model: str = "nanonets-ocr-3"
    extractor_reasoning: dict[str, Any] | None = None
    extractor_max_workers: int = 7

    # === Section-specific extractor overrides ===
    # Map section name → SectionOverride to use a different model for that section.
    # Example: {"progressive_score": SectionOverride(provider="openrouter", model="google/gemini-3.5-flash", reasoning={"effort": "high"})}
    section_overrides: dict[str, SectionOverride] = field(default_factory=dict)

    # === Enhancement Phase ===
    # Grid removal mode for the progressive_score section:
    #   False / "off"    — no grid removal (default)
    #   "inpaint"        — morphological grid detection + cv2.inpaint
    #   "handwriting"    — grid removal + restore handwritten marks (HSV + morphology)
    grid_removal: str | bool = False

    # Gamma correction value applied before CLAHE:
    #   None or 1.0 — disable gamma correction
    #   0.7         — darken overexposed images (recommended for FIBA photos)
    gamma: float | None = 0.7

    # === Validation Phase ===
    # List of plugin names to run. None = core plugins only (default).
    # Use "all" to run every registered plugin.
    # Examples: ["core_quarter_sums", "fiba_player_fouls", "referee_player_points_sum"]
    validation_plugins: list[str] | str | None = None

    # === API Keys (optional, auto-loaded from env) ===
    interfaze_api_key: str | None = None
    gemini_api_key: str | None = None
    glm_api_key: str | None = None
    docstrange_api_key: str | None = None
    qubrid_api_key: str | None = None
    openrouter_api_key: str | None = None

    def __post_init__(self):
        if self.interfaze_api_key is None:
            self.interfaze_api_key = (
                os.getenv("INTERFAZE_API_KEY") or os.getenv("INTERFAZE_KEY")
            )
        if self.gemini_api_key is None:
            self.gemini_api_key = (
                os.getenv("GOOGLE_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_GENAI_API_KEY")
            )
        if self.glm_api_key is None:
            self.glm_api_key = (
                os.getenv("GLM_API_KEY") or os.getenv("ZAI_API_KEY")
            )
        if self.docstrange_api_key is None:
            self.docstrange_api_key = os.getenv("DOCSTRANGE_API_KEY")
        if self.qubrid_api_key is None:
            self.qubrid_api_key = os.getenv("QUBRID_API_KEY")
        if self.openrouter_api_key is None:
            self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

    def get_cropper_api_key(self) -> str:
        """Get the API key for the cropper provider."""
        key = self._resolve_api_key(self.cropper_provider)
        if not key:
            raise ValueError(f"Falta API key para cropper ({self.cropper_provider})")
        return key

    def get_extractor_api_key(self) -> str:
        """Get the API key for the extractor provider."""
        key = self._resolve_api_key(self.extractor_provider)
        if not key:
            raise ValueError(f"Falta API key para extractor ({self.extractor_provider})")
        return key

    def _resolve_api_key(self, provider: str) -> str | None:
        """Resolve the API key for a given provider."""
        if provider == "gemini":
            return self.gemini_api_key
        elif provider == "glm":
            return self.glm_api_key
        elif provider == "docstrange":
            return self.docstrange_api_key
        elif provider == "qubrid":
            return self.qubrid_api_key
        elif provider == "openrouter":
            return self.openrouter_api_key
        else:
            return self.interfaze_api_key

    def get_section_override(self, section_name: str) -> SectionOverride | None:
        """Get the override for a section, if any."""
        return self.section_overrides.get(section_name)

    def get_override_api_key(self, override: SectionOverride) -> str:
        """Get the API key for a section override provider."""
        key = self._resolve_api_key(override.provider)
        if not key:
            raise ValueError(f"Falta API key para override ({override.provider})")
        return key
