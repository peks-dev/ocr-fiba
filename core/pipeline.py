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
from pathlib import Path
from typing import Any

from config.pipeline_config import PipelineConfig
from core.toolbox import OcrToolbox
from core.types import RunContext
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
        self.last_context: RunContext | None = None

    def process(
        self,
        image_path: Path,
        output_dir: Path | None = None,
        *,
        run_id: str | None = None,
        runs_dir: Path = Path("runs"),
        use_run_layout: bool = False,
    ) -> dict[str, Any]:
        """
        Run the full pipeline on a FIBA scoresheet image.

        Args:
            image_path: Path to a raw photo of a FIBA scoresheet.
                        The preprocessor will isolate the sheet automatically.
            output_dir: Directory for intermediate outputs. Defaults to outputs/<stem>-sections.
            run_id: Optional run identifier for canonical run layout.
            runs_dir: Base directory for canonical run layout.
            use_run_layout: Store artifacts under runs/{run_id}/.

        Returns:
            Final extracted and validated JSON result.
        """
        print(f"\n=== FIBA OCR Pipeline (Model-Agnostic) ===", file=sys.stderr)
        print(f"Imagen: {image_path.name}", file=sys.stderr)
        print(f"Cropper : {self.config.cropper_provider} ({self.config.cropper_model})", file=sys.stderr)
        print(f"Extractor: {self.config.extractor_provider} ({self.config.extractor_model})", file=sys.stderr)
        for section_name, provider in self.extractor.section_providers.items():
            print(f"  Override [{section_name}]: {provider.name} ({provider.model_name})", file=sys.stderr)
        print(file=sys.stderr)

        pipeline_result = self.toolbox.run_full_pipeline(
            image_path,
            output_dir=output_dir,
            run_id=run_id,
            runs_dir=runs_dir,
            use_run_layout=use_run_layout,
            progress_callback=self._print_progress,
        )
        result = pipeline_result.data["result"]
        self.total_usage = _to_token_usage(pipeline_result.usage) if pipeline_result.usage else TokenUsage()
        self.last_context = pipeline_result.data["context"]

        print(f"\nPipeline finalizado.", file=sys.stderr)
        print(f"Estado: {result.get('match_status')}", file=sys.stderr)
        print(f"Total tokens: {self.total_usage.total_tokens}", file=sys.stderr)

        return result

    def save_result(self, result: dict[str, Any], output_path: Path) -> None:
        """Save the result JSON to a file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Resultado guardado en: {output_path}", file=sys.stderr)

    def _print_progress(self, event: str, payload: dict[str, Any]) -> None:
        if event != "step_start" and event != "step_complete":
            return

        step = payload.get("step")
        if event == "step_start":
            self._print_step_start(str(step))
            return

        result = payload.get("result")
        if result is None:
            return
        self._print_step_complete(str(step), result)

    def _print_step_start(self, step: str) -> None:
        if step == "preprocess_sheet":
            print("[0/7] Aislando hoja y corrigiendo perspectiva...", file=sys.stderr)
        elif step == "detect_sections":
            print("[1/7] Detectando y recortando secciones principales...", file=sys.stderr)
        elif step == "crop_team_fouls":
            print("[2/7] Recortando faltas de equipo...", file=sys.stderr)
        elif step == "enhance_sections":
            from core.enhancer import _normalize_grid_mode

            grid_mode = _normalize_grid_mode(self.config.grid_removal)
            grid_label = {
                "off": "",
                "inpaint": " (con eliminación de rejilla)",
                "handwriting": " (con eliminación de rejilla + protección de escritura)",
            }[grid_mode]
            gamma_label = f" γ={self.config.gamma}" if self.config.gamma and self.config.gamma != 1.0 else ""
            print(f"[3/7] Mejorando imágenes{grid_label}{gamma_label}...", file=sys.stderr)
        elif step == "extract_sections":
            print("[4/7] Extrayendo datos...", file=sys.stderr)
        elif step == "build_final_output":
            print("[5/7] Construyendo resultado final...", file=sys.stderr)
        elif step == "validate_result":
            print("[6/7] Ejecutando validación...", file=sys.stderr)
            print(f"  Plugins activos: {self.validation_engine.active_plugins}", file=sys.stderr)

    def _print_step_complete(self, step: str, result) -> None:
        if step == "preprocess_sheet":
            processed_image = Path(result.data["processed_image"])
            if result.warnings:
                warning = result.warnings[0]
                print(f"  Preprocesamiento falló ({warning.get('message')}), usando imagen original", file=sys.stderr)
            else:
                print(f"  Hoja aislada: {processed_image.name}", file=sys.stderr)
        elif step in {"detect_sections", "crop_team_fouls"}:
            for box in result.data["pixel_boxes"]:
                print(f"  - {box.name}: x={box.x}, y={box.y}, w={box.width}, h={box.height}", file=sys.stderr)
        elif step == "enhance_sections":
            for name in result.data["enhanced"]:
                print(f"  - {name}", file=sys.stderr)


def _to_token_usage(usage) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )
