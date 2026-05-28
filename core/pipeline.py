"""
FibaOcrPipeline — Complete pipeline orchestrator (model-agnostic).

This module orchestrates the full FIBA scoresheet OCR pipeline:
0. Sheet isolation (Preprocessor)
1. Section detection and cropping (Cropper)
2. Team fouls sub-cropping (Cropper)
3. Image enhancement (Enhancer)
4. Data extraction per section (Extractor)
5. Output normalization (OutputBuilder)
6. Validation (validation module)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from config.pipeline_config import PipelineConfig
from core.toolbox import OcrToolbox
from core.tracing import RunTracer
from providers.base import TokenUsage


class FibaOcrPipeline:
    """
    Pipeline completo para procesar hojas de anotación FIBA.
    Usa la arquitectura model-agnostic.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.total_usage = TokenUsage()
        self.toolbox = OcrToolbox(config)
        self.cropper = self.toolbox.cropper
        self.extractor = self.toolbox.extractor
        self.validation_engine = self.toolbox.validation_engine

    def process(self, image_path: Path, output_dir: Path | None = None) -> dict[str, Any]:
        """
        Run the full pipeline on a FIBA scoresheet image.

        Args:
            image_path: Path to a raw photo of a FIBA scoresheet.
                        The preprocessor will isolate the sheet automatically.
            output_dir: Directory for intermediate outputs. Defaults to outputs/<stem>-sections.

        Returns:
            Final extracted and validated JSON result.
        """
        if output_dir is None:
            output_dir = Path("outputs") / f"{image_path.stem}-sections"
        context = self.toolbox.create_context(image_path, output_dir)
        tracer = RunTracer(context)
        self.total_usage = TokenUsage()

        print(f"\n=== FIBA OCR Pipeline (Model-Agnostic) ===", file=sys.stderr)
        print(f"Imagen: {image_path.name}", file=sys.stderr)
        print(f"Cropper : {self.config.cropper_provider} ({self.config.cropper_model})", file=sys.stderr)
        print(f"Extractor: {self.config.extractor_provider} ({self.config.extractor_model})", file=sys.stderr)
        for section_name, provider in self.extractor.section_providers.items():
            print(f"  Override [{section_name}]: {provider.name} ({provider.model_name})", file=sys.stderr)
        print(file=sys.stderr)

        started = time.monotonic()

        # [0/7] Preprocess: isolate sheet from photo, correct perspective
        print("[0/7] Aislando hoja y corrigiendo perspectiva...", file=sys.stderr)
        preprocess_result = self.toolbox.preprocess_sheet(context, tracer=tracer)
        processed_image = Path(preprocess_result.data["processed_image"])
        if preprocess_result.warnings:
            warning = preprocess_result.warnings[0]
            print(f"  Preprocesamiento falló ({warning.get('message')}), usando imagen original", file=sys.stderr)
        else:
            print(f"  Hoja aislada: {processed_image.name}", file=sys.stderr)

        # [1/7] Detect and crop main sections
        print("[1/7] Detectando y recortando secciones principales...", file=sys.stderr)
        detection_result = self.toolbox.detect_sections(context, processed_image, tracer=tracer)
        pixel_boxes = detection_result.data["pixel_boxes"]
        if detection_result.usage:
            self.total_usage.add(_to_token_usage(detection_result.usage))
        for box in pixel_boxes:
            print(f"  - {box.name}: x={box.x}, y={box.y}, w={box.width}, h={box.height}", file=sys.stderr)

        # [2/7] Sub-crop team fouls
        print("[2/7] Recortando faltas de equipo...", file=sys.stderr)
        fouls_result = self.toolbox.crop_team_fouls(context, tracer=tracer)
        fouls_boxes = fouls_result.data["pixel_boxes"]
        if fouls_result.usage:
            self.total_usage.add(_to_token_usage(fouls_result.usage))
        for box in fouls_boxes:
            print(f"  - {box.name}: x={box.x}, y={box.y}, w={box.width}, h={box.height}", file=sys.stderr)

        # [3/7] Enhance section images (gamma + CLAHE + grid removal + sharpening)
        from core.enhancer import _normalize_grid_mode
        grid_mode = _normalize_grid_mode(self.config.grid_removal)
        grid_label = {
            "off": "",
            "inpaint": " (con eliminación de rejilla)",
            "handwriting": " (con eliminación de rejilla + protección de escritura)",
        }[grid_mode]
        gamma_label = f" γ={self.config.gamma}" if self.config.gamma and self.config.gamma != 1.0 else ""
        print(f"[3/7] Mejorando imágenes{grid_label}{gamma_label}...", file=sys.stderr)
        enhance_result = self.toolbox.enhance_sections(context, tracer=tracer)
        enhanced = enhance_result.data["enhanced"]
        for name in enhanced:
            print(f"  - {name}", file=sys.stderr)

        # [4/7] Extract data from all sections
        print("[4/7] Extrayendo datos...", file=sys.stderr)
        extraction_result = self.toolbox.extract_sections(context, tracer=tracer)
        extracted = extraction_result.data["extracted"]
        if extraction_result.usage:
            self.total_usage.add(_to_token_usage(extraction_result.usage))

        # [5/7] Build normalized output
        print("[5/7] Construyendo resultado final...", file=sys.stderr)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        build_result = self.toolbox.build_final_output(
            context,
            extracted,
            processing_time_ms=elapsed_ms,
            token_usage=self.total_usage,
            tracer=tracer,
        )
        result = build_result.data["result"]

        # [6/7] Validate
        print("[6/7] Ejecutando validación...", file=sys.stderr)
        print(f"  Plugins activos: {self.validation_engine.active_plugins}", file=sys.stderr)
        validation_result = self.toolbox.validate_result(context, result, tracer=tracer)
        result = validation_result.data["result"]

        print(f"\nPipeline finalizado.", file=sys.stderr)
        print(f"Estado: {result.get('match_status')}", file=sys.stderr)
        print(f"Total tokens: {self.total_usage.total_tokens}", file=sys.stderr)
        tracer.write()

        return result

    def save_result(self, result: dict[str, Any], output_path: Path) -> None:
        """Save the result JSON to a file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Resultado guardado en: {output_path}", file=sys.stderr)


def _to_token_usage(usage) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )
