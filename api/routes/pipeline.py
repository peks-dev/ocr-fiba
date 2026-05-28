from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import PipelineOptions, RunFullPipelineRequest
from config.pipeline_config import PipelineConfig, SectionOverride
from core.exceptions import OcrEngineError
from core.toolbox import OcrToolbox

router = APIRouter(prefix="/v1/pipeline", tags=["pipeline"])


@router.post("/full")
def run_full_pipeline(request: RunFullPipelineRequest) -> dict:
    image_path = Path(request.image_path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Input image not found: {image_path}")

    try:
        toolbox = OcrToolbox(_build_config(request.options))
        result = toolbox.run_full_pipeline(
            image_path,
            run_id=request.run_id,
            runs_dir=Path(request.runs_dir),
            use_run_layout=True,
        )
        return result.to_dict()
    except OcrEngineError as exc:
        raise HTTPException(status_code=422, detail=exc.to_dict()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _build_config(options: PipelineOptions) -> PipelineConfig:
    section_overrides = {
        name: SectionOverride(
            provider=override.provider,
            model=override.model,
            reasoning=override.reasoning,
            max_tokens=override.max_tokens,
        )
        for name, override in options.section_overrides.items()
    }
    return PipelineConfig(
        cropper_provider=options.cropper_provider,
        cropper_model=options.cropper_model,
        extractor_provider=options.extractor_provider,
        extractor_model=options.extractor_model,
        extractor_reasoning=options.extractor_reasoning,
        extractor_max_workers=options.extractor_max_workers,
        section_overrides=section_overrides,
        validation_plugins=options.validation_plugins,
        grid_removal=options.grid_removal,
        gamma=options.gamma,
    )
