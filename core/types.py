"""
Shared contracts for the OCR engine tool layer.

These types are intentionally lightweight and JSON-serializable so they can be
used by the pipeline, CLI, HTTP API, MCP server, and future batch workflows.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Literal


ToolStatus = Literal["pending", "running", "completed", "failed", "skipped"]


def new_run_id() -> str:
    """Create a compact, sortable-enough run identifier for local executions."""
    return f"run_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def to_jsonable(value: Any) -> Any:
    """Convert engine values to plain JSON-compatible structures."""
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


@dataclass(frozen=True)
class ProviderUsage:
    """Usage reported by a model/provider call."""

    provider: str | None = None
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_usage(
        cls,
        usage: Any,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> ProviderUsage:
        """Build usage from TokenUsage or a usage dict."""
        if usage is None:
            return cls(provider=provider, model=model)
        if isinstance(usage, dict):
            return cls(
                provider=provider,
                model=model,
                prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                total_tokens=int(usage.get("total_tokens", 0) or 0),
            )
        return cls(
            provider=provider,
            model=model,
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class Artifact:
    """A file or structured payload produced by an engine step."""

    name: str
    path: Path | None = None
    kind: str = "file"
    mime_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass
class StepTrace:
    """Audit record for one engine step."""

    step: str
    status: ToolStatus = "pending"
    section: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    duration_ms: int | None = None
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    usage: ProviderUsage | None = None
    error: dict[str, Any] | None = None

    @classmethod
    def start(
        cls,
        step: str,
        *,
        section: str | None = None,
        input: dict[str, Any] | None = None,
    ) -> StepTrace:
        return cls(
            step=step,
            section=section,
            status="running",
            started_at=time.time(),
            input=input or {},
        )

    def complete(
        self,
        *,
        output: dict[str, Any] | None = None,
        artifacts: list[Artifact] | None = None,
        warnings: list[dict[str, Any]] | None = None,
        usage: ProviderUsage | None = None,
    ) -> None:
        self.status = "completed"
        self.completed_at = time.time()
        self.duration_ms = _duration_ms(self.started_at, self.completed_at)
        if output:
            self.output.update(output)
        if artifacts:
            self.artifacts.extend(artifacts)
        if warnings:
            self.warnings.extend(warnings)
        if usage:
            self.usage = usage

    def fail(self, error: dict[str, Any]) -> None:
        self.status = "failed"
        self.completed_at = time.time()
        self.duration_ms = _duration_ms(self.started_at, self.completed_at)
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass
class RunContext:
    """Execution context shared by tool-layer operations."""

    run_id: str
    input_path: Path
    output_dir: Path
    artifacts_dir: Path
    raw_dir: Path
    trace_path: Path

    @classmethod
    def create(
        cls,
        input_path: Path,
        output_dir: Path,
        *,
        run_id: str | None = None,
    ) -> RunContext:
        run_id = run_id or new_run_id()
        return cls(
            run_id=run_id,
            input_path=input_path,
            output_dir=output_dir,
            artifacts_dir=output_dir,
            raw_dir=output_dir / "raw",
            trace_path=output_dir / "trace.json",
        )

    def ensure_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def artifact(self, name: str, *, kind: str = "file", mime_type: str | None = None) -> Artifact:
        return Artifact(name=name, path=self.artifacts_dir / name, kind=kind, mime_type=mime_type)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass
class ToolResult:
    """Structured response returned by each engine tool operation."""

    success: bool
    run_id: str
    step: str
    status: ToolStatus
    data: dict[str, Any] = field(default_factory=dict)
    section: str | None = None
    artifacts: list[Artifact] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    usage: ProviderUsage | None = None
    trace: list[StepTrace] = field(default_factory=list)
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


def _duration_ms(started_at: float | None, completed_at: float | None) -> int | None:
    if started_at is None or completed_at is None:
        return None
    return int((completed_at - started_at) * 1000)
