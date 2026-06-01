from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiSettings:
    env: str
    api_key: str | None
    runs_dir: Path
    max_upload_mb: int

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def get_api_settings() -> ApiSettings:
    env = os.getenv("OCR_ENV", "development").strip().lower() or "development"
    settings = ApiSettings(
        env=env,
        api_key=os.getenv("OCR_ENGINE_API_KEY"),
        runs_dir=Path(os.getenv("OCR_RUNS_DIR", "runs")),
        max_upload_mb=int(os.getenv("OCR_MAX_UPLOAD_MB", "20")),
    )
    validate_api_settings(settings)
    return settings


def validate_api_settings(settings: ApiSettings) -> None:
    if settings.is_production and not settings.api_key:
        raise RuntimeError("OCR_ENGINE_API_KEY is required when OCR_ENV=production")
    if settings.max_upload_mb < 1:
        raise RuntimeError("OCR_MAX_UPLOAD_MB must be at least 1")


def resolve_runs_dir(requested_runs_dir: str | Path | None = None) -> Path:
    settings = get_api_settings()
    if settings.is_production:
        return settings.runs_dir
    return Path(requested_runs_dir) if requested_runs_dir else settings.runs_dir
