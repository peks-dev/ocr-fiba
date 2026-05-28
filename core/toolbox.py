"""
Agent-ready tool layer for the FIBA OCR engine.

The toolbox exposes atomic operations over the existing OCR components. It does
not replace Cropper, Extractor, or ValidationEngine; it gives callers a stable
structured contract around them.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from config.pipeline_config import PipelineConfig
from core.artifacts import ArtifactStore
from core.cropper import Cropper
from core.enhancer import enhance_sections as enhance_section_images
from core.extractor import Extractor
from core.output_builder import build_final_output as build_output
from core.preprocessor import preprocess_sheet as isolate_sheet
from core.tracing import RunTracer
from core.types import Artifact, ProviderUsage, RunContext, StepTrace, ToolResult
from providers import create_provider
from providers.base import TokenUsage
from validation import ValidationEngine


class OcrToolbox:
    """Composable OCR operations with structured results and tracing."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.cropper = Cropper.from_config(
            provider_type=config.cropper_provider,
            model_name=config.cropper_model,
            api_key=config.get_cropper_api_key(),
        )
        self.extractor = self._build_extractor(config)
        self.validation_engine = ValidationEngine(plugins=config.validation_plugins)

    def create_context(
        self,
        image_path: Path,
        output_dir: Path | None = None,
        *,
        run_id: str | None = None,
        runs_dir: Path = Path("runs"),
        use_run_layout: bool = False,
    ) -> RunContext:
        if use_run_layout:
            return RunContext.create_run(image_path, runs_dir, run_id=run_id)
        if output_dir is None:
            output_dir = Path("outputs") / f"{image_path.stem}-sections"
        return RunContext.create(image_path, output_dir, run_id=run_id)

    def preprocess_sheet(
        self,
        context: RunContext,
        *,
        tracer: RunTracer | None = None,
    ) -> ToolResult:
        preprocessed_path = context.output_dir / f"{context.input_path.stem}-recortada.jpg"
        warnings: list[dict[str, Any]] = []

        with self._step(
            context,
            tracer,
            "preprocess_sheet",
            input={"image_path": context.input_path},
        ) as (trace, active_tracer):
            try:
                isolate_sheet(context.input_path, preprocessed_path)
                processed_image = preprocessed_path
                artifacts = [
                    Artifact(
                        name=preprocessed_path.name,
                        path=preprocessed_path,
                        kind="image",
                        mime_type="image/jpeg",
                    )
                ]
                output = {"processed_image": processed_image, "used_fallback": False}
            except ValueError as exc:
                processed_image = context.input_path
                artifacts = []
                warning = {
                    "type": "preprocess_fallback",
                    "message": str(exc),
                    "fallback": "original_image",
                }
                warnings.append(warning)
                output = {"processed_image": processed_image, "used_fallback": True}

            trace.complete(output=output, artifacts=artifacts, warnings=warnings)
            return self._success(
                context,
                active_tracer,
                trace,
                data=output,
                artifacts=artifacts,
                warnings=warnings,
            )

    def detect_sections(
        self,
        context: RunContext,
        image_path: Path,
        *,
        tracer: RunTracer | None = None,
    ) -> ToolResult:
        with self._step(
            context,
            tracer,
            "detect_sections",
            input={"image_path": image_path},
        ) as (trace, active_tracer):
            pixel_boxes, meta = self.cropper.detect_and_crop_sections(
                image_path, context.output_dir
            )
            usage = ProviderUsage.from_usage(
                meta.usage,
                provider=meta.detector,
                model=meta.model,
            )
            artifacts = [
                Artifact(name="boxes.json", path=context.output_dir / "boxes.json", kind="json"),
                *[
                    Artifact(
                        name=f"{box.name}.png",
                        path=context.output_dir / f"{box.name}.png",
                        kind="image",
                        mime_type="image/png",
                    )
                    for box in pixel_boxes
                ],
            ]
            data = {
                "pixel_boxes": pixel_boxes,
                "sections": [box.name for box in pixel_boxes],
                "meta": meta,
            }
            trace.complete(
                output={"sections": data["sections"]},
                artifacts=artifacts,
                usage=usage,
            )
            return self._success(
                context,
                active_tracer,
                trace,
                data=data,
                artifacts=artifacts,
                usage=usage,
            )

    def crop_team_fouls(
        self,
        context: RunContext,
        *,
        tracer: RunTracer | None = None,
    ) -> ToolResult:
        with self._step(
            context,
            tracer,
            "crop_team_fouls",
            input={"sections_dir": context.output_dir},
        ) as (trace, active_tracer):
            fouls_boxes, meta = self.cropper.detect_and_crop_team_fouls(context.output_dir)
            usage = ProviderUsage.from_usage(
                meta.usage,
                provider=meta.detector,
                model=meta.model,
            )
            artifacts = [
                Artifact(name="fouls_boxes.json", path=context.output_dir / "fouls_boxes.json", kind="json"),
                *[
                    Artifact(
                        name=f"{box.name}.png",
                        path=context.output_dir / f"{box.name}.png",
                        kind="image",
                        mime_type="image/png",
                    )
                    for box in fouls_boxes
                ],
            ]
            data = {
                "pixel_boxes": fouls_boxes,
                "sections": [box.name for box in fouls_boxes],
                "meta": meta,
            }
            trace.complete(
                output={"sections": data["sections"]},
                artifacts=artifacts,
                usage=usage,
            )
            return self._success(
                context,
                active_tracer,
                trace,
                data=data,
                artifacts=artifacts,
                usage=usage,
            )

    def enhance_sections(
        self,
        context: RunContext,
        *,
        tracer: RunTracer | None = None,
    ) -> ToolResult:
        with self._step(
            context,
            tracer,
            "enhance_sections",
            input={
                "sections_dir": context.output_dir,
                "grid_removal": self.config.grid_removal,
                "gamma": self.config.gamma,
            },
        ) as (trace, active_tracer):
            enhanced = enhance_section_images(
                context.output_dir,
                grid_removal=self.config.grid_removal,
                gamma=self.config.gamma,
            )
            artifacts = [
                Artifact(
                    name=name,
                    path=context.output_dir / name,
                    kind="image",
                    mime_type="image/png",
                )
                for name in enhanced
            ]
            data = {"enhanced": enhanced}
            trace.complete(output=data, artifacts=artifacts)
            return self._success(
                context,
                active_tracer,
                trace,
                data=data,
                artifacts=artifacts,
            )

    def extract_sections(
        self,
        context: RunContext,
        *,
        tracer: RunTracer | None = None,
    ) -> ToolResult:
        with self._step(
            context,
            tracer,
            "extract_sections",
            input={"sections_dir": context.output_dir},
        ) as (trace, active_tracer):
            extracted, usage_raw = self.extractor.extract_all_sections(
                context.output_dir,
                max_workers=self.config.extractor_max_workers,
            )
            usage = ProviderUsage.from_usage(
                usage_raw,
                provider=self.config.extractor_provider,
                model=self.config.extractor_model,
            )
            sections = [key for key in extracted.keys() if key != "_meta"]
            data = {"extracted": extracted, "sections": sections}
            trace.complete(output={"sections": sections}, usage=usage)
            return self._success(
                context,
                active_tracer,
                trace,
                data=data,
                usage=usage,
            )

    def build_final_output(
        self,
        context: RunContext,
        extracted: dict[str, Any],
        *,
        processing_time_ms: int,
        token_usage: TokenUsage,
        tracer: RunTracer | None = None,
    ) -> ToolResult:
        with self._step(context, tracer, "build_final_output") as (trace, active_tracer):
            result = build_output(
                extracted,
                processing_time_ms=processing_time_ms,
                model=self.config.extractor_model,
                token_usage={
                    "prompt_tokens": token_usage.prompt_tokens,
                    "completion_tokens": token_usage.completion_tokens,
                    "total_tokens": token_usage.total_tokens,
                },
            )
            result["meta"]["cropper"] = f"{self.config.cropper_provider}:{self.config.cropper_model}"
            result["meta"]["extractor"] = f"{self.config.extractor_provider}:{self.config.extractor_model}"
            output = {
                "has_header": bool(result.get("header")),
                "has_team_a": bool(result.get("team_a")),
                "has_team_b": bool(result.get("team_b")),
                "has_progressive_score": bool(result.get("progressive_score")),
                "has_footer": bool(result.get("footer")),
            }
            trace.complete(output=output)
            return self._success(
                context,
                active_tracer,
                trace,
                data={"result": result, **output},
            )

    def validate_result(
        self,
        context: RunContext,
        result: dict[str, Any],
        *,
        tracer: RunTracer | None = None,
    ) -> ToolResult:
        with self._step(
            context,
            tracer,
            "validate_result",
            input={"plugins": self.validation_engine.active_plugins},
        ) as (trace, active_tracer):
            validated = self.validation_engine.validate(result)
            warnings = validated.get("validation_warnings", [])
            output = {
                "match_status": validated.get("match_status"),
                "warnings": len(warnings),
            }
            trace.complete(output=output, warnings=warnings)
            return self._success(
                context,
                active_tracer,
                trace,
                data={"result": validated, **output},
                warnings=warnings,
            )

    def run_full_pipeline(
        self,
        image_path: Path,
        output_dir: Path | None = None,
        *,
        run_id: str | None = None,
        runs_dir: Path = Path("runs"),
        use_run_layout: bool = False,
    ) -> ToolResult:
        context = self.create_context(
            image_path,
            output_dir,
            run_id=run_id,
            runs_dir=runs_dir,
            use_run_layout=use_run_layout,
        )
        tracer = RunTracer(context)
        artifact_store = ArtifactStore(context)
        input_artifact = artifact_store.copy_input()
        total_usage = TokenUsage()
        started = time.monotonic()

        preprocess = self.preprocess_sheet(context, tracer=tracer)
        processed_image = Path(preprocess.data["processed_image"])

        detection = self.detect_sections(context, processed_image, tracer=tracer)
        crop_usage = detection.usage
        if crop_usage:
            total_usage.add(_to_token_usage(crop_usage))

        fouls = self.crop_team_fouls(context, tracer=tracer)
        fouls_usage = fouls.usage
        if fouls_usage:
            total_usage.add(_to_token_usage(fouls_usage))

        self.enhance_sections(context, tracer=tracer)

        extraction = self.extract_sections(context, tracer=tracer)
        extract_usage = extraction.usage
        if extract_usage:
            total_usage.add(_to_token_usage(extract_usage))

        elapsed_ms = int((time.monotonic() - started) * 1000)
        built = self.build_final_output(
            context,
            extraction.data["extracted"],
            processing_time_ms=elapsed_ms,
            token_usage=total_usage,
            tracer=tracer,
        )
        validated = self.validate_result(context, built.data["result"], tracer=tracer)
        result_artifact = artifact_store.write_result(validated.data["result"])
        tracer.write()
        trace_artifact = artifact_store.add_file(
            context.trace_path,
            name="trace.json",
            kind="trace",
            mime_type="application/json",
        )

        return ToolResult(
            success=True,
            run_id=context.run_id,
            step="run_full_pipeline",
            status="completed",
            data={
                "result": validated.data["result"],
                "total_usage": total_usage,
                "context": context,
            },
            artifacts=[input_artifact, result_artifact, trace_artifact],
            warnings=validated.warnings,
            usage=ProviderUsage.from_usage(
                total_usage,
                provider=self.config.extractor_provider,
                model=self.config.extractor_model,
            ),
            trace=tracer.steps,
        )

    def _build_extractor(self, config: PipelineConfig) -> Extractor:
        section_providers = {}
        section_max_tokens = {}
        for section_name, override in config.section_overrides.items():
            api_key = config.get_override_api_key(override)
            kwargs = {}
            if override.reasoning:
                kwargs["reasoning"] = override.reasoning
            section_providers[section_name] = create_provider(
                override.provider,
                override.model,
                api_key,
                **kwargs,
            )
            if override.max_tokens is not None:
                section_max_tokens[section_name] = override.max_tokens

        extractor = Extractor.from_config(
            provider_type=config.extractor_provider,
            model_name=config.extractor_model,
            api_key=config.get_extractor_api_key(),
            reasoning=config.extractor_reasoning,
        )
        if section_providers:
            extractor.section_providers = section_providers
        if section_max_tokens:
            extractor.section_max_tokens = section_max_tokens
        return extractor

    @contextmanager
    def _step(
        self,
        context: RunContext,
        tracer: RunTracer | None,
        name: str,
        *,
        input: dict[str, Any] | None = None,
    ) -> Iterator[tuple[StepTrace, RunTracer]]:
        context.ensure_dirs()
        active_tracer = tracer or RunTracer(context)
        with active_tracer.step(name, input=input) as trace:
            yield trace, active_tracer
        if tracer is None:
            active_tracer.write()

    @staticmethod
    def _success(
        context: RunContext,
        tracer: RunTracer,
        trace: StepTrace,
        *,
        data: dict[str, Any],
        artifacts: list[Artifact] | None = None,
        warnings: list[dict[str, Any]] | None = None,
        usage: ProviderUsage | None = None,
    ) -> ToolResult:
        return ToolResult(
            success=True,
            run_id=context.run_id,
            step=trace.step,
            status=trace.status,
            data=data,
            section=trace.section,
            artifacts=artifacts or [],
            warnings=warnings or [],
            usage=usage,
            trace=tracer.steps,
        )


def _to_token_usage(usage: ProviderUsage) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )
