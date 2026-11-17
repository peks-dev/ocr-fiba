from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ocr_engine_core.config.pipeline_config import (
    DEFAULT_CROPPER_MODEL,
    DEFAULT_CROPPER_PROVIDER,
    DEFAULT_EXTRACTOR_MODEL,
    DEFAULT_EXTRACTOR_PROVIDER,
    default_extractor_reasoning,
)


ProviderName = Literal["interfaze", "gemini", "glm", "docstrange", "qubrid", "openrouter"]


class SectionOverrideRequest(BaseModel):
    provider: ProviderName
    model: str
    reasoning: dict[str, Any] | None = None
    max_tokens: int | None = None


class PipelineOptions(BaseModel):
    cropper_provider: ProviderName = DEFAULT_CROPPER_PROVIDER
    cropper_model: str = DEFAULT_CROPPER_MODEL
    extractor_provider: ProviderName = DEFAULT_EXTRACTOR_PROVIDER
    extractor_model: str = DEFAULT_EXTRACTOR_MODEL
    extractor_reasoning: dict[str, Any] | None = Field(default_factory=default_extractor_reasoning)
    extractor_max_workers: int = 7
    section_overrides: dict[str, SectionOverrideRequest] = Field(default_factory=dict)
    validation_plugins: list[str] | Literal["all"] | None = None
    grid_removal: Literal[False, "inpaint", "handwriting"] = False
    gamma: float | None = 0.7


class CreateRunRequest(BaseModel):
    image_path: str
    run_id: str | None = None
    runs_dir: str = "runs"
    options: PipelineOptions = Field(default_factory=PipelineOptions)
