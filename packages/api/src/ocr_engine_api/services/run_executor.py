from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ocr_engine_api.services.run_repository import (
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    RunRepository,
)
from ocr_engine_core.config.pipeline_config import PipelineConfig
from ocr_engine_core.exceptions import OcrEngineError
from ocr_engine_core.toolbox import OcrToolbox


_RUN_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr-run")


class RunExecutor:
    """Execute OCR runs and update filesystem-backed status."""

    def __init__(self, repository: RunRepository) -> None:
        self.repository = repository

    def submit_full_pipeline(
        self,
        image_path: Path,
        *,
        run_id: str,
        runs_dir: Path,
        config: PipelineConfig,
    ) -> Future[dict[str, Any]]:
        """Submit a local/preview run without holding the HTTP response open."""
        return _RUN_EXECUTOR.submit(
            self.run_full_pipeline,
            image_path,
            run_id=run_id,
            runs_dir=runs_dir,
            config=config,
        )

    def run_full_pipeline(
        self,
        image_path: Path,
        *,
        run_id: str,
        runs_dir: Path,
        config: PipelineConfig,
    ) -> dict[str, Any]:
        self.repository.update_status(
            run_id,
            status=RUN_STATUS_RUNNING,
            progress={"current_step": "pipeline_start", "completed_steps": [], "step_count": None},
        )
        completed_steps: list[str] = []

        try:
            toolbox = OcrToolbox(config)
            result = toolbox.run_full_pipeline(
                image_path,
                run_id=run_id,
                runs_dir=runs_dir,
                use_run_layout=True,
                progress_callback=lambda event, payload: self._handle_progress(
                    run_id,
                    event,
                    completed_steps=completed_steps,
                    payload=payload,
                ),
            )
            self.repository.update_status(
                run_id,
                status=RUN_STATUS_COMPLETED,
                progress={
                    "current_step": "completed",
                    "completed_steps": completed_steps,
                    "step_count": len(completed_steps),
                },
            )
            return result.to_dict()
        except Exception as exc:
            error = (
                exc.to_dict()
                if isinstance(exc, OcrEngineError)
                else {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "OCR pipeline failed",
                    "retryable": False,
                }
            )
            self.repository.update_status(
                run_id,
                status=RUN_STATUS_FAILED,
                error=error,
            )
            raise

    def _handle_progress(
        self,
        run_id: str,
        event: str,
        *,
        completed_steps: list[str],
        payload: dict[str, Any],
    ) -> None:
        step = payload.get("step")
        if event == "step_complete" and isinstance(step, str) and step not in completed_steps:
            completed_steps.append(step)

        current_step = step if isinstance(step, str) else event
        self.repository.update_status(
            run_id,
            status=RUN_STATUS_RUNNING,
            progress={
                "current_step": current_step,
                "completed_steps": completed_steps,
                "step_count": None,
            },
        )
