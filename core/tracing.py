"""
Trace recording for OCR engine runs.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from core.types import RunContext, StepTrace, to_jsonable


class RunTracer:
    """Collects step traces and persists them as JSON."""

    def __init__(self, context: RunContext):
        self.context = context
        self._steps: list[StepTrace] = []

    @property
    def steps(self) -> list[StepTrace]:
        return list(self._steps)

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
        return to_jsonable(
            {
                "run_id": self.context.run_id,
                "layout": self.context.layout,
                "input": self.context.input_path,
                "run_dir": self.context.run_dir,
                "output_dir": self.context.output_dir,
                "artifacts_dir": self.context.artifacts_dir,
                "raw_dir": self.context.raw_dir,
                "result_path": self.context.result_path,
                "steps": self._steps,
            }
        )


def _exception_to_dict(exc: Exception) -> dict[str, Any]:
    if hasattr(exc, "to_dict"):
        return exc.to_dict()
    return {
        "type": exc.__class__.__name__,
        "message": str(exc),
    }
