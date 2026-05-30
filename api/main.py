from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.auth import is_auth_exempt, is_authorized, unauthorized_response
from api.routes import pipeline, runs
from api.settings import get_api_settings
from helpers.image_utils import load_dotenv


def create_app() -> FastAPI:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    settings = get_api_settings()

    app = FastAPI(
        title="FIBA OCR Engine API",
        version="0.1.0",
    )
    app.include_router(pipeline.router)
    app.include_router(runs.router)

    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        if is_auth_exempt(request.url.path):
            return await call_next(request)
        if not is_authorized(request.headers.get("authorization", ""), settings.api_key):
            return unauthorized_response()
        return await call_next(request)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
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


app = create_app()
