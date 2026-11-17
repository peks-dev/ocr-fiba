"""
Core Cropper — Model-agnostic section detection, validation, and cropping.

This module contains all the business logic for detecting bounding boxes,
validating them, and cropping sections from FIBA scoresheet images.
It uses a ModelProvider for the actual AI calls but keeps validation
and cropping logic provider-independent.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal, cast

from ocr_engine_core.exceptions import CroppingError, ErrorCode
from ocr_engine_core.utils.image_utils import read_image, write_png
from ocr_engine_core.providers.base import BoundingBox, DetectionMeta, PixelBox, TokenUsage
from ocr_engine_core.providers import create_provider, ProviderType
from ocr_engine_core.prompts.cropping import CROPPING_PROMPT
from ocr_engine_core.prompts.team_fouls_cropping import TEAM_FOULS_CROPPING_PROMPT
from ocr_engine_core.resources.schemas import load_schema


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECTION_NAMES = ("header", "team_a", "team_b", "progressive_score", "footer")

SectionName = Literal["header", "team_a", "team_b", "progressive_score", "footer"]

# Minimum cropped side in pixels (clamped to source image bounds for tiny test images).
MIN_CROP_DIM_PX = 16


# ---------------------------------------------------------------------------
# Cropper class
# ---------------------------------------------------------------------------

class Cropper:
    """
    Responsible for detecting and cropping sections from a FIBA scoresheet image.
    Uses a ModelProvider to detect bounding boxes, then validates and crops.
    """

    def __init__(self, provider):
        self.provider = provider

    @classmethod
    def from_config(cls, provider_type: ProviderType, model_name: str, api_key: str):
        """Factory method to create a Cropper from configuration."""
        provider = create_provider(provider_type, model_name, api_key)
        return cls(provider)

    # ===================================================================
    # Main section cropping (5 sections)
    # ===================================================================

    def detect_and_crop_sections(
        self,
        image_path: Path,
        output_dir: Path,
    ) -> tuple[list[PixelBox], DetectionMeta]:
        """
        Detect main sections, validate bounding boxes, and crop.

        Detection and cropping both run on ``image_path``. Section images are
        enhanced afterwards (see ``enhancer.enhance_sections``), so the crop is
        taken from the raw isolated sheet on purpose.

        Args:
            image_path: Image used for detection and cropping.
            output_dir: Directory for cropped section images.

        Returns:
            Tuple of (pixel_boxes, detection_meta).
        """
        started = time.monotonic()

        # Detect — always on the detection image (color)
        schema = load_schema("cropping", provider=self.provider.name)
        boxes, usage = self.provider.detect_bounding_boxes(
            image_path, CROPPING_PROMPT, schema, max_tokens=2000
        )

        # Validate
        validated = self._validate_boxes(boxes)

        # Crop from the same isolated sheet used for detection
        pixel_boxes = self._crop_sections(image_path, validated, output_dir)

        elapsed_ms = int((time.monotonic() - started) * 1000)
        meta = DetectionMeta(
            detector=self.provider.name,
            model=self.provider.model_name,
            processing_time_ms=elapsed_ms,
            usage={
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            },
        )

        # Save boxes.json
        self._save_boxes_json(output_dir, image_path, validated, pixel_boxes, meta)

        return pixel_boxes, meta

    # ===================================================================
    # Team fouls sub-cropping
    # ===================================================================

    def detect_and_crop_team_fouls(
        self,
        sections_dir: Path,
    ) -> tuple[list[PixelBox], DetectionMeta]:
        """
        Sub-crop team fouls from already-cropped team sections.

        For each team (team_a, team_b):
        1. Detect the 'Faltas de Equipo' bounding box within the team section.
        2. Validate the box.
        3. Crop and save as team_a_fouls.png / team_b_fouls.png.

        Returns:
            Tuple of (fouls_pixel_boxes, combined_meta).
        """
        started = time.monotonic()
        teams = ("team_a", "team_b")
        result: list[PixelBox] = []
        fouls_data: dict[str, Any] = {
            "source_sections": {},
            "normalized_boxes": [],
            "pixel_boxes": [],
            "per_team_meta": {},
        }
        total_usage = TokenUsage()

        # Validate inputs up-front (cheap, deterministic) before spending LLM calls.
        for team in teams:
            team_image_path = sections_dir / f"{team}.png"
            if not team_image_path.exists():
                raise CroppingError(
                    f"No existe la sección de equipo requerida: {team_image_path}",
                    code=ErrorCode.CROP_SECTION_NOT_FOUND,
                )

        # Detect both team-fouls boxes in parallel (network-bound LLM calls).
        with ThreadPoolExecutor(max_workers=len(teams)) as executor:
            detections = dict(
                zip(teams, executor.map(lambda t: self._detect_team_fouls(sections_dir, t), teams))
            )

        # Crop, write, and accumulate metadata sequentially (deterministic order).
        for team in teams:
            boxes, usage = detections[team]
            total_usage.add(usage)

            if not boxes:
                raise CroppingError(
                    f"El detector no devolvió bounding box para faltas de {team}",
                    code=ErrorCode.CROP_TEAM_FOULS_NOT_FOUND,
                )

            # Validate
            fouls_box = self._validate_team_fouls_box(boxes[0])

            # Crop
            team_image = read_image(sections_dir / f"{team}.png")
            h, w = team_image.shape[:2]
            fouls_pixel = self._to_pixel_box(fouls_box, w, h)

            fouls_name = f"{team}_fouls"
            self._crop_and_save_box(team_image, fouls_pixel, sections_dir / f"{fouls_name}.png")
            result.append(fouls_pixel)

            # Track data
            fouls_data["source_sections"][team] = f"{team}.png"
            fouls_data["normalized_boxes"].append(asdict(fouls_box))
            fouls_data["pixel_boxes"].append(asdict(fouls_pixel))
            fouls_data["per_team_meta"][team] = {
                "detector": self.provider.name,
                "model": self.provider.model_name,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                },
            }

        # Save fouls_boxes.json
        elapsed_ms = int((time.monotonic() - started) * 1000)
        meta = DetectionMeta(
            detector=self.provider.name,
            model=self.provider.model_name,
            processing_time_ms=elapsed_ms,
            usage={
                "prompt_tokens": total_usage.prompt_tokens,
                "completion_tokens": total_usage.completion_tokens,
                "total_tokens": total_usage.total_tokens,
            },
        )
        fouls_data["meta"] = {
            "detector": meta.detector,
            "model": meta.model,
            "processing_time_ms": meta.processing_time_ms,
            "usage": meta.usage,
        }
        fouls_json_path = sections_dir / "fouls_boxes.json"
        fouls_json_path.write_text(
            json.dumps(fouls_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        return result, meta

    def _detect_team_fouls(
        self,
        sections_dir: Path,
        team: str,
    ) -> tuple[list[BoundingBox], TokenUsage]:
        """Detect the team-fouls bounding box for one team (network-bound)."""
        team_image_path = sections_dir / f"{team}.png"
        schema = load_schema("team_fouls_cropping", provider=self.provider.name)
        return self.provider.detect_bounding_boxes(
            team_image_path, TEAM_FOULS_CROPPING_PROMPT, schema, max_tokens=2000
        )

    # ===================================================================
    # Validation methods (migrated from crop_sections.py)
    # ===================================================================

    def _validate_boxes(self, boxes: list[BoundingBox]) -> list[BoundingBox]:
        """Validate and normalize a list of detected bounding boxes."""
        boxes_by_name: dict[str, BoundingBox] = {}
        for box in boxes:
            name = self._normalize_section_name(box.name)
            self._validate_normalized_box(box)
            validated = BoundingBox(
                name=name,
                x_min=box.x_min,
                y_min=box.y_min,
                x_max=box.x_max,
                y_max=box.y_max,
                confidence=box.confidence,
            )
            boxes_by_name[validated.name] = validated

        missing = [name for name in SECTION_NAMES if name not in boxes_by_name]
        if missing:
            raise CroppingError(
                f"El detector no devolvió estas secciones: {', '.join(missing)}",
                code=ErrorCode.CROP_SECTION_NOT_FOUND,
            )
        return [boxes_by_name[name] for name in SECTION_NAMES]

    def _validate_team_fouls_box(self, box: BoundingBox) -> BoundingBox:
        """Validate a single team fouls bounding box."""
        name = self._normalize_team_fouls_name(box.name)
        self._validate_normalized_box(box)
        return BoundingBox(
            name=name,
            x_min=box.x_min,
            y_min=box.y_min,
            x_max=box.x_max,
            y_max=box.y_max,
            confidence=box.confidence,
        )

    @staticmethod
    def _normalize_section_name(value: str) -> SectionName:
        """Normalize section names, handling common aliases."""
        name = str(value).strip()
        aliases = {
            "progressive_scoring": "progressive_score",
            "progresive_score": "progressive_score",
            "final_score": "footer",
        }
        name = aliases.get(name, name)
        if name not in SECTION_NAMES:
            raise CroppingError(f"Nombre de sección inválido: {name}", code=ErrorCode.CROP_INVALID_BOX)
        return cast(SectionName, name)

    @staticmethod
    def _normalize_team_fouls_name(value: str) -> str:
        """Normalize team fouls section name."""
        name = str(value).strip().lower()
        valid_names = {
            "team_fouls",
            "fouls",
            "team fouls",
            "faltas de equipo",
            "fouls_section",
        }
        if name in valid_names:
            return "team_fouls"
        raise CroppingError(f"Nombre inválido para faltas de equipo: {name}", code=ErrorCode.CROP_INVALID_BOX)

    @staticmethod
    def _validate_normalized_box(box: BoundingBox) -> None:
        """Validate that normalized coordinates are in 0..1000 range and box is valid."""
        values = (box.x_min, box.y_min, box.x_max, box.y_max)
        if any(value < 0 or value > 1000 for value in values):
            raise CroppingError(
                f"Coordenadas fuera de 0..1000 para {box.name}: {values}",
                code=ErrorCode.CROP_INVALID_BOX,
            )
        if box.x_max <= box.x_min or box.y_max <= box.y_min:
            raise CroppingError(f"Bounding box inválido para {box.name}: {values}", code=ErrorCode.CROP_INVALID_BOX)

    # ===================================================================
    # Cropping methods
    # ===================================================================

    def _crop_sections(
        self,
        image_path: Path,
        boxes: list[BoundingBox],
        output_dir: Path,
    ) -> list[PixelBox]:
        """Crop sections from the source image based on validated bounding boxes."""
        image = read_image(image_path)
        height, width = image.shape[:2]
        pixel_boxes = [self._to_pixel_box(box, width, height) for box in boxes]
        self._validate_layout(pixel_boxes, width, height)

        output_dir.mkdir(parents=True, exist_ok=True)
        for box in pixel_boxes:
            self._crop_and_save_box(image, box, output_dir / f"{box.name}.png")

        return pixel_boxes

    @staticmethod
    def _crop_and_save_box(image: Any, box: PixelBox, output_path: Path) -> None:
        """Slice one validated PixelBox from image and write it as PNG."""
        crop = image[box.y : box.y + box.height, box.x : box.x + box.width]
        if crop.size == 0:
            raise CroppingError(f"El recorte de {output_path.stem} quedó vacío", code=ErrorCode.CROP_EMPTY_CROP)
        write_png(output_path, crop)

    @staticmethod
    def _to_pixel_box(box: BoundingBox, image_width: int, image_height: int) -> PixelBox:
        """Convert a normalized (0-1000) bounding box to pixel coordinates."""
        if image_width <= 0 or image_height <= 0:
            raise CroppingError(
                f"Dimensiones de imagen inválidas para {box.name}: {image_width}x{image_height}",
                code=ErrorCode.CROP_EMPTY_CROP,
            )

        x1 = max(0, min(round(box.x_min / 1000 * image_width), image_width))
        y1 = max(0, min(round(box.y_min / 1000 * image_height), image_height))
        x2 = max(0, min(round(box.x_max / 1000 * image_width), image_width))
        y2 = max(0, min(round(box.y_max / 1000 * image_height), image_height))

        width = x2 - x1
        height = y2 - y1
        if width <= 0 or height <= 0:
            raise CroppingError(
                f"El recorte de {box.name} quedó vacío ({width}x{height}px)",
                code=ErrorCode.CROP_EMPTY_CROP,
            )

        min_side = min(MIN_CROP_DIM_PX, image_width, image_height)
        if width < min_side or height < min_side:
            raise CroppingError(
                f"El recorte de {box.name} es demasiado pequeño ({width}x{height}px)",
                code=ErrorCode.CROP_EMPTY_CROP,
            )

        return PixelBox(
            name=box.name,
            x=x1,
            y=y1,
            width=width,
            height=height,
            confidence=box.confidence,
        )

    @staticmethod
    def _validate_layout(boxes: list[PixelBox], image_width: int, image_height: int) -> None:
        """Validate that the detected layout makes sense for a FIBA scoresheet."""
        by_name = {box.name: box for box in boxes}
        if by_name["header"].y >= by_name["team_a"].y:
            raise CroppingError(
                "Layout inválido: header debe estar arriba de team_a",
                code=ErrorCode.CROP_LAYOUT_INVALID,
            )
        if by_name["team_a"].y >= by_name["team_b"].y:
            raise CroppingError(
                "Layout inválido: team_a debe estar arriba de team_b",
                code=ErrorCode.CROP_LAYOUT_INVALID,
            )
        if by_name["team_b"].y >= by_name["footer"].y:
            raise CroppingError(
                "Layout inválido: team_b debe estar arriba de footer",
                code=ErrorCode.CROP_LAYOUT_INVALID,
            )
        if by_name["header"].y > int(image_height * 0.20):
            raise CroppingError(
                "Layout sospechoso: header no está en la parte superior",
                code=ErrorCode.CROP_LAYOUT_INVALID,
            )
        if by_name["footer"].y < int(image_height * 0.65):
            raise CroppingError(
                "Layout sospechoso: footer no está en la parte inferior",
                code=ErrorCode.CROP_LAYOUT_INVALID,
            )
        if by_name["progressive_score"].x < int(image_width * 0.35):
            raise CroppingError(
                "Layout sospechoso: progressive_score debería estar hacia la derecha",
                code=ErrorCode.CROP_LAYOUT_INVALID,
            )

    @staticmethod
    def _save_boxes_json(
        output_dir: Path,
        image_path: Path,
        boxes: list[BoundingBox],
        pixel_boxes: list[PixelBox],
        meta: DetectionMeta,
    ) -> None:
        """Save boxes.json alongside cropped sections."""
        (output_dir / "boxes.json").write_text(
            json.dumps(
                {
                    "source_image": str(image_path),
                    "image_size": None,  # filled by caller if needed
                    "normalized_boxes": [asdict(box) for box in boxes],
                    "pixel_boxes": [asdict(box) for box in pixel_boxes],
                    "meta": {
                        "detector": meta.detector,
                        "model": meta.model,
                        "processing_time_ms": meta.processing_time_ms,
                        "usage": meta.usage,
                    },
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
