from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ProviderName = Literal["interfaze", "gemini", "glm", "docstrange", "qubrid", "openrouter"]


class SectionOverrideRequest(BaseModel):
    provider: ProviderName
    model: str
    reasoning: dict[str, Any] | None = None
    max_tokens: int | None = None


class PipelineOptions(BaseModel):
    cropper_provider: ProviderName = "openrouter"
    cropper_model: str = "google/gemini-3-flash-preview"
    extractor_provider: ProviderName = "openrouter"
    extractor_model: str = "google/gemini-3-flash-preview"
    extractor_reasoning: dict[str, Any] | None = None
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
