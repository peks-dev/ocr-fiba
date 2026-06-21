"""
Base abstraction for AI model providers.

This module defines the common interface that all model providers
(Interfaze, Gemini, OpenRouter, etc.) must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


DetectorName = Literal["interfaze", "gemini", "glm", "docstrange", "qubrid", "openrouter"]


@dataclass
class TokenUsage:
    """Represents token usage from a model call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        # Providers may report usage fields as null; coerce to 0 so token
        # aggregation never hits `int + None` (TypeError) mid-run.
        self.prompt_tokens = int(self.prompt_tokens or 0)
        self.completion_tokens = int(self.completion_tokens or 0)
        self.total_tokens = int(self.total_tokens or 0)

    def add(self, other: TokenUsage) -> None:
        self.prompt_tokens += int(other.prompt_tokens or 0)
        self.completion_tokens += int(other.completion_tokens or 0)
        self.total_tokens += int(other.total_tokens or 0)


@dataclass(frozen=True)
class BoundingBox:
    """Normalized bounding box (0-1000 scale)."""
    name: str
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    confidence: float | None = None


@dataclass(frozen=True)
class PixelBox:
    """Pixel-level bounding box."""
    name: str
    x: int
    y: int
    width: int
    height: int
    confidence: float | None = None


@dataclass
class DetectionMeta:
    """Metadata from a detection call."""
    detector: str
    model: str
    processing_time_ms: int
    usage: dict[str, Any] = field(default_factory=dict)


class ModelProvider(ABC):
    """
    Abstract base class for all model providers.

    Each provider (Interfaze, Gemini, OpenRouter, etc.) must implement
    this interface to be used in the pipeline.
    """

    name: str
    model_name: str

    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key

    @abstractmethod
    def structured_completion(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 4000,
    ) -> tuple[dict[str, Any], TokenUsage]:
        """
        Perform a completion on an image.

        If schema is provided, uses structured JSON output (response_format).
        If schema is None, allows free-form text output (e.g. Markdown).

        Args:
            image_path: Path to the image file.
            prompt: Text prompt describing what to extract.
            schema: JSON schema for structured output, or None for free-form.
            max_tokens: Maximum tokens for the response.

        Returns:
            Tuple of (parsed_result, token_usage).
            When schema is None and response is not JSON, result is {"raw_text": content}.
        """
        ...

    @abstractmethod
    def detect_bounding_boxes(
        self,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int = 2000,
    ) -> tuple[list[BoundingBox], TokenUsage]:
        """
        Detect bounding boxes in an image (used for section cropping).

        Args:
            image_path: Path to the image.
            prompt: Prompt instructing the model how to detect sections.
            schema: JSON schema for the bounding boxes response.
            max_tokens: Maximum tokens for the response.

        Returns:
            Tuple of (list_of_boxes, token_usage).
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name})"
