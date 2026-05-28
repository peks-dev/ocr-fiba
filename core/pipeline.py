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

from config.pipeline_config import PipelineConfig, SectionOverride
from core.cropper import Cropper
from core.enhancer import enhance_sections
from core.extractor import Extractor
from core.output_builder import build_final_output
from core.preprocessor import preprocess_sheet
from core.tracing import RunTracer
from core.types import Artifact, ProviderUsage, RunContext
from providers.base import TokenUsage
from providers import create_provider
from validation import ValidationEngine


class FibaOcrPipeline:
    """
    Pipeline completo para procesar hojas de anotación FIBA.
    Usa la arquitectura model-agnostic.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.total_usage = TokenUsage()

        self.cropper = Cropper.from_config(
            provider_type=config.cropper_provider,
            model_name=config.cropper_model,
            api_key=config.get_cropper_api_key(),
        )

        # Build section-specific provider overrides
        section_providers = {}
        section_max_tokens = {}
        for section_name, override in config.section_overrides.items():
            api_key = config.get_override_api_key(override)
            kwargs = {}
            if override.reasoning:
                kwargs["reasoning"] = override.reasoning
            section_providers[section_name] = create_provider(
                override.provider, override.model, api_key, **kwargs,
            )
            if override.max_tokens is not None:
                section_max_tokens[section_name] = override.max_tokens

        self.extractor = Extractor.from_config(
            provider_type=config.extractor_provider,
            model_name=config.extractor_model,
            api_key=config.get_extractor_api_key(),
            reasoning=config.extractor_reasoning,
        )
        # Attach section overrides
        if section_providers:
            self.extractor.section_providers = section_providers
        if section_max_tokens:
            self.extractor.section_max_tokens = section_max_tokens

        self.validation_engine = ValidationEngine(
            plugins=config.validation_plugins,
        )

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
        context = RunContext.create(image_path, output_dir)
        tracer = RunTracer(context)

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
        context.ensure_dirs()
        preprocessed_path = output_dir / f"{image_path.stem}-recortada.jpg"
        with tracer.step("preprocess_sheet", input={"image_path": image_path}) as trace:
            try:
                preprocess_sheet(image_path, preprocessed_path)
                print(f"  Hoja aislada: {preprocessed_path.name}", file=sys.stderr)
                processed_image = preprocessed_path
                trace.complete(
                    output={"processed_image": processed_image},
                    artifacts=[
                        Artifact(
                            name=preprocessed_path.name,
                            path=preprocessed_path,
                            kind="image",
                            mime_type="image/jpeg",
                        )
                    ],
                )
            except ValueError as e:
                print(f"  Preprocesamiento falló ({e}), usando imagen original", file=sys.stderr)
                processed_image = image_path
                trace.complete(
                    output={"processed_image": processed_image},
                    warnings=[
                        {
                            "type": "preprocess_fallback",
                            "message": str(e),
                            "fallback": "original_image",
                        }
                    ],
                )

        # [1/7] Detect and crop main sections
        print("[1/7] Detectando y recortando secciones principales...", file=sys.stderr)
        with tracer.step("detect_sections", input={"image_path": processed_image}) as trace:
            pixel_boxes, crop_meta = self.cropper.detect_and_crop_sections(
                processed_image, output_dir
            )
            trace.complete(
                output={"sections": [box.name for box in pixel_boxes]},
                artifacts=[
                    Artifact(name="boxes.json", path=output_dir / "boxes.json", kind="json"),
                    *[
                        Artifact(
                            name=f"{box.name}.png",
                            path=output_dir / f"{box.name}.png",
                            kind="image",
                            mime_type="image/png",
                        )
                        for box in pixel_boxes
                    ],
                ],
                usage=ProviderUsage.from_usage(
                    crop_meta.usage,
                    provider=crop_meta.detector,
                    model=crop_meta.model,
                ),
            )
        self.total_usage.add(TokenUsage(
            prompt_tokens=crop_meta.usage.get("prompt_tokens", 0) or 0,
            completion_tokens=crop_meta.usage.get("completion_tokens", 0) or 0,
            total_tokens=crop_meta.usage.get("total_tokens", 0) or 0,
        ))
        for box in pixel_boxes:
            print(f"  - {box.name}: x={box.x}, y={box.y}, w={box.width}, h={box.height}", file=sys.stderr)

        # [2/7] Sub-crop team fouls
        print("[2/7] Recortando faltas de equipo...", file=sys.stderr)
        with tracer.step("crop_team_fouls", input={"sections_dir": output_dir}) as trace:
            fouls_boxes, fouls_meta = self.cropper.detect_and_crop_team_fouls(output_dir)
            trace.complete(
                output={"sections": [box.name for box in fouls_boxes]},
                artifacts=[
                    Artifact(name="fouls_boxes.json", path=output_dir / "fouls_boxes.json", kind="json"),
                    *[
                        Artifact(
                            name=f"{box.name}.png",
                            path=output_dir / f"{box.name}.png",
                            kind="image",
                            mime_type="image/png",
                        )
                        for box in fouls_boxes
                    ],
                ],
                usage=ProviderUsage.from_usage(
                    fouls_meta.usage,
                    provider=fouls_meta.detector,
                    model=fouls_meta.model,
                ),
            )
        self.total_usage.add(TokenUsage(
            prompt_tokens=fouls_meta.usage.get("prompt_tokens", 0) or 0,
            completion_tokens=fouls_meta.usage.get("completion_tokens", 0) or 0,
            total_tokens=fouls_meta.usage.get("total_tokens", 0) or 0,
        ))
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
        with tracer.step(
            "enhance_sections",
            input={
                "sections_dir": output_dir,
                "grid_removal": self.config.grid_removal,
                "gamma": self.config.gamma,
            },
        ) as trace:
            enhanced = enhance_sections(
                output_dir,
                grid_removal=self.config.grid_removal,
                gamma=self.config.gamma,
            )
            trace.complete(
                output={"enhanced": enhanced},
                artifacts=[
                    Artifact(
                        name=name,
                        path=output_dir / name,
                        kind="image",
                        mime_type="image/png",
                    )
                    for name in enhanced
                ],
            )
        for name in enhanced:
            print(f"  - {name}", file=sys.stderr)

        # [4/7] Extract data from all sections
        print("[4/7] Extrayendo datos...", file=sys.stderr)
        with tracer.step("extract_sections", input={"sections_dir": output_dir}) as trace:
            extracted, extract_usage = self.extractor.extract_all_sections(
                output_dir,
                max_workers=self.config.extractor_max_workers,
            )
            trace.complete(
                output={"sections": [key for key in extracted.keys() if key != "_meta"]},
                usage=ProviderUsage.from_usage(
                    extract_usage,
                    provider=self.config.extractor_provider,
                    model=self.config.extractor_model,
                ),
            )
        self.total_usage.add(extract_usage)

        # [5/7] Build normalized output
        print("[5/7] Construyendo resultado final...", file=sys.stderr)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        with tracer.step("build_final_output") as trace:
            result = build_final_output(
                extracted,
                processing_time_ms=elapsed_ms,
                model=self.config.extractor_model,
                token_usage={
                    "prompt_tokens": self.total_usage.prompt_tokens,
                    "completion_tokens": self.total_usage.completion_tokens,
                    "total_tokens": self.total_usage.total_tokens,
                },
            )
            trace.complete(
                output={
                    "has_header": bool(result.get("header")),
                    "has_team_a": bool(result.get("team_a")),
                    "has_team_b": bool(result.get("team_b")),
                    "has_progressive_score": bool(result.get("progressive_score")),
                    "has_footer": bool(result.get("footer")),
                }
            )

        # Add cropper info to meta
        result["meta"]["cropper"] = f"{self.config.cropper_provider}:{self.config.cropper_model}"
        result["meta"]["extractor"] = f"{self.config.extractor_provider}:{self.config.extractor_model}"

        # [6/7] Validate
        print("[6/7] Ejecutando validación...", file=sys.stderr)
        print(f"  Plugins activos: {self.validation_engine.active_plugins}", file=sys.stderr)
        with tracer.step(
            "validate_result",
            input={"plugins": self.validation_engine.active_plugins},
        ) as trace:
            result = self.validation_engine.validate(result)
            trace.complete(
                output={
                    "match_status": result.get("match_status"),
                    "warnings": len(result.get("validation_warnings", [])),
                },
                warnings=result.get("validation_warnings", []),
            )

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
