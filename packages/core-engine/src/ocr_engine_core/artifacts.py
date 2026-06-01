"""
Helpers for recording OCR run artifacts.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ocr_engine_core.types import Artifact, RunContext, to_jsonable


class ArtifactStore:
    """Small filesystem-backed artifact registry for one run."""

    def __init__(self, context: RunContext):
        self.context = context
        self._artifacts: list[Artifact] = []

    @property
    def artifacts(self) -> list[Artifact]:
        return list(self._artifacts)

    def add_file(
        self,
        path: Path,
        *,
        name: str | None = None,
        kind: str = "file",
        mime_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        artifact = Artifact(
            name=name or path.name,
            path=path,
            kind=kind,
            mime_type=mime_type,
            metadata=metadata or {},
        )
        self._artifacts.append(artifact)
        return artifact

    def copy_input(self) -> Artifact:
        """Copy the source image into the run input directory."""
        self.context.ensure_dirs()
        destination = self.context.input_dir / self.context.input_path.name
        if self.context.input_path.resolve() != destination.resolve():
            shutil.copy2(self.context.input_path, destination)
        return self.add_file(
            destination,
            name=f"input/{destination.name}",
            kind="input",
            mime_type=_guess_image_mime_type(destination),
            metadata={"source_path": str(self.context.input_path)},
        )

    def write_json(
        self,
        name: str,
        data: Any,
        *,
        kind: str = "json",
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        self.context.ensure_dirs()
        path = self.context.artifacts_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(to_jsonable(data), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return self.add_file(
            path,
            name=name,
            kind=kind,
            mime_type="application/json",
            metadata=metadata,
        )

    def write_result(self, data: Any) -> Artifact:
        """Write the final engine result to the run result path."""
        self.context.ensure_dirs()
        self.context.result_path.write_text(
            json.dumps(to_jsonable(data), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return self.add_file(
            self.context.result_path,
            name="result.json",
            kind="result",
            mime_type="application/json",
        )

    def to_list(self) -> list[dict[str, Any]]:
        return [artifact.to_dict() for artifact in self._artifacts]


def _guess_image_mime_type(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return None
