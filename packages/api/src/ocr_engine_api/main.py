from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ocr_engine_api.auth import is_auth_exempt, is_authorized, unauthorized_response
from ocr_engine_api.auth_api_key import is_api_key_request, validate_api_key
from ocr_engine_api.rate_limit import RunRateLimiter, client_key, is_run_creation, rate_limited_response
from ocr_engine_api.routes import me, runs
from ocr_engine_api.settings import get_api_settings
from ocr_engine_core.utils.image_utils import load_dotenv


def create_app() -> FastAPI:
    _load_project_env()
    settings = get_api_settings()

    app = FastAPI(
        title="FIBA OCR Engine API",
        version="0.1.0",
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(runs.router)
    rate_limiter = RunRateLimiter(
        settings.rate_limit_per_minute,
        settings.rate_limit_per_day,
        state_file=settings.rate_limit_state_file,
    )
    app.state.rate_limiter = rate_limiter

    if settings.has_supabase:
        app.include_router(me.router)

    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        if request.method == "OPTIONS" or is_auth_exempt(request.url.path):
            return await call_next(request)

        # /v1/me/* endpoints handle their own auth via Supabase JWT dependency
        if request.url.path.startswith("/v1/me/"):
            return await call_next(request)

        # API key validation: Supabase-backed ocr_* keys, else static bearer fallback.
        if settings.has_supabase and is_api_key_request(request):
            result = validate_api_key(request)
            if result is not None:
                return result
        else:
            auth_header = request.headers.get("authorization", "")
            if not is_authorized(auth_header, settings.api_key):
                return unauthorized_response()

        if is_run_creation(request.method, request.url.path):
            auth_header = request.headers.get("authorization", "")
            client_host = request.client.host if request.client else None
            allowed, window, retry_after = rate_limiter.check(client_key(auth_header, client_host))
            if not allowed:
                limit = rate_limiter.per_minute if window == "minute" else rate_limiter.per_day
                return rate_limited_response(window or "minute", retry_after, limit)
        return await call_next(request)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Internal server error",
                    "retryable": False,
                },
            },
        )

    return app



def _load_project_env() -> None:
    """Load .env from cwd or the repository root without overriding env vars."""
    candidates: list[Path] = []

    cwd = Path.cwd().resolve()
    candidates.extend([cwd / ".env", *(parent / ".env" for parent in cwd.parents)])

    module_path = Path(__file__).resolve()
    candidates.extend(parent / ".env" for parent in module_path.parents)

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            load_dotenv(candidate)
            return


app = create_app()


def run() -> None:
    """Run the API app with uvicorn for the ocr-api console script."""
    import uvicorn

    host = os.getenv("OCR_API_HOST", "0.0.0.0")
    port = int(os.getenv("OCR_API_PORT") or os.getenv("PORT") or "8000")
    uvicorn.run("ocr_engine_api.main:app", host=host, port=port, reload=False)
