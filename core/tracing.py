"""
Trace recording for OCR engine runs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from core.types import Artifact, ProviderUsage, RunContext, StepTrace, to_jsonable


class RunTracer:
    """Collects step traces and persists them as JSON."""

    def __init__(self, context: RunContext):
        self.context = context
        self._steps: list[StepTrace] = []
        self._run_artifacts: list[Artifact] = []
        self._result_summary: dict[str, Any] = {}

    @property
    def steps(self) -> list[StepTrace]:
        return list(self._steps)

    def set_run_artifacts(self, artifacts: list[Artifact]) -> None:
        self._run_artifacts = list(artifacts)

    def set_result_summary(self, summary: dict[str, Any]) -> None:
        self._result_summary = dict(summary)

    @contextmanager
    def step(
        self,
        name: str,
        *,
        section: str | None = None,
        input: dict[str, Any] | None = None,
    ) -> Iterator[StepTrace]:
        trace = StepTrace.start(name, section=section, input=input)
        self._steps.append(trace)
        try:
            yield trace
        except Exception as exc:
            trace.fail(_exception_to_dict(exc))
            self.write()
            raise

    def write(self) -> None:
        self.context.ensure_dirs()
        self.context.trace_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def to_dict(self) -> dict[str, Any]:
        summary = self._summary()
        return to_jsonable(
            {
                "run_id": self.context.run_id,
                "status": summary["status"],
                "layout": self.context.layout,
                "input": self.context.input_path,
                "run_dir": self.context.run_dir,
                "output_dir": self.context.output_dir,
                "artifacts_dir": self.context.artifacts_dir,
                "raw_dir": self.context.raw_dir,
                "result_path": self.context.result_path,
                "started_at": summary["started_at"],
                "completed_at": summary["completed_at"],
                "started_at_iso": _timestamp_iso(summary["started_at"]),
                "completed_at_iso": _timestamp_iso(summary["completed_at"]),
                "duration_ms": summary["duration_ms"],
                "step_count": len(self._steps),
                "warning_count": summary["warning_count"],
                "artifact_count": summary["artifact_count"],
                "total_usage": summary["total_usage"],
                "result_summary": self._result_summary,
                "run_artifacts": self._run_artifacts,
                "steps": self._steps,
            }
        )

    def _summary(self) -> dict[str, Any]:
        started_values = [step.started_at for step in self._steps if step.started_at is not None]
        completed_values = [step.completed_at for step in self._steps if step.completed_at is not None]
        started_at = min(started_values) if started_values else None
        completed_at = max(completed_values) if completed_values else None
        duration_ms = None
        if started_at is not None and completed_at is not None:
            duration_ms = int((completed_at - started_at) * 1000)
        status = "failed" if any(step.status == "failed" for step in self._steps) else "completed"
        if any(step.status == "running" for step in self._steps):
            status = "running"
        if not self._steps:
            status = "pending"
        total_usage = _sum_usage(step.usage for step in self._steps)
        return {
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "warning_count": sum(len(step.warnings) for step in self._steps),
            "artifact_count": sum(len(step.artifacts) for step in self._steps) + len(self._run_artifacts),
            "total_usage": total_usage,
        }


def _exception_to_dict(exc: Exception) -> dict[str, Any]:
    if hasattr(exc, "to_dict"):
        return exc.to_dict()
    return {
        "type": exc.__class__.__name__,
        "message": str(exc),
    }


def _sum_usage(usages: Iterator[ProviderUsage | None]) -> ProviderUsage:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    providers: set[str] = set()
    models: set[str] = set()
    for usage in usages:
        if usage is None:
            continue
        prompt_tokens += usage.prompt_tokens
        completion_tokens += usage.completion_tokens
        total_tokens += usage.total_tokens
        if usage.provider:
            providers.add(usage.provider)
        if usage.model:
            models.add(usage.model)
    return ProviderUsage(
        provider=",".join(sorted(providers)) or None,
        model=",".join(sorted(models)) or None,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


def _timestamp_iso(value: float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
