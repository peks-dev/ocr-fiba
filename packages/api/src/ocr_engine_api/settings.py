from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ocr_engine_core.config.pipeline_config import parse_reasoning_config


@dataclass(frozen=True)
class ApiSettings:
    env: str
    api_key: str | None
    runs_dir: Path
    max_upload_mb: int
    supabase_url: str
    supabase_service_key: str
    supabase_publishable_key: str
    supabase_jwt_secret: str
    cors_origins: tuple[str, ...]
    allow_path_input: bool = True
    rate_limit_per_minute: int = 0
    rate_limit_per_day: int = 0
    rate_limit_state_file: Path | None = None
    default_extractor_provider: str | None = None
    default_extractor_model: str | None = None
    default_extractor_reasoning: str | None = None
    stale_run_seconds: int = 900

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key and self.supabase_jwt_secret)

    @property
    def has_supabase_service(self) -> bool:
        """True when the service-role client can be constructed (URL + service key)."""
        return bool(self.supabase_url and self.supabase_service_key)


def get_api_settings() -> ApiSettings:
    env = os.getenv("OCR_ENV", "development").strip().lower() or "development"
    settings = ApiSettings(
        env=env,
        api_key=os.getenv("OCR_ENGINE_API_KEY"),
        runs_dir=Path(os.getenv("OCR_RUNS_DIR", "runs")),
        max_upload_mb=int(os.getenv("OCR_MAX_UPLOAD_MB", "20")),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
        supabase_publishable_key=(
            os.getenv("SUPABASE_PUBLISHABLE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
            or ""
        ),
        supabase_jwt_secret=os.getenv("SUPABASE_JWT_SECRET", ""),
        cors_origins=parse_cors_origins(os.getenv("OCR_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")),
        # Server-path image reads (POST /v1/runs {image_path}) are off by default in production.
        allow_path_input=_env_bool("OCR_ALLOW_PATH_INPUT", default=env != "production"),
        # Run-creation quotas per bearer token (0 = unlimited). Defaults only apply in production.
        rate_limit_per_minute=int(os.getenv("OCR_RATE_LIMIT_PER_MINUTE", "3" if env == "production" else "0")),
        rate_limit_per_day=int(os.getenv("OCR_RATE_LIMIT_PER_DAY", "50" if env == "production" else "0")),
        rate_limit_state_file=Path(os.environ["OCR_RATE_LIMIT_STATE_FILE"]) if os.getenv("OCR_RATE_LIMIT_STATE_FILE") else None,
        default_extractor_provider=os.getenv("OCR_DEFAULT_EXTRACTOR_PROVIDER") or None,
        default_extractor_model=os.getenv("OCR_DEFAULT_EXTRACTOR_MODEL") or None,
        default_extractor_reasoning=os.getenv("OCR_DEFAULT_EXTRACTOR_REASONING") or None,
        stale_run_seconds=int(os.getenv("OCR_STALE_RUN_SECONDS", "900")),
    )
    validate_api_settings(settings)
    return settings


def validate_api_settings(settings: ApiSettings) -> None:
    if settings.is_production and not settings.api_key:
        raise RuntimeError("OCR_ENGINE_API_KEY is required when OCR_ENV=production")
    if settings.max_upload_mb < 1:
        raise RuntimeError("OCR_MAX_UPLOAD_MB must be at least 1")
    if settings.rate_limit_per_minute < 0 or settings.rate_limit_per_day < 0:
        raise RuntimeError("OCR_RATE_LIMIT_PER_MINUTE / OCR_RATE_LIMIT_PER_DAY must be >= 0")
    if settings.stale_run_seconds < 0:
        raise RuntimeError("OCR_STALE_RUN_SECONDS must be >= 0")
    if settings.default_extractor_reasoning is not None:
        try:
            parse_reasoning_config(settings.default_extractor_reasoning)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc


def resolve_runs_dir(requested_runs_dir: str | Path | None = None) -> Path:
    settings = get_api_settings()
    if settings.is_production:
        return settings.runs_dir
    return Path(requested_runs_dir) if requested_runs_dir else settings.runs_dir


def parse_cors_origins(value: str) -> tuple[str, ...]:
    """Parse comma-separated CORS origins from environment."""
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
