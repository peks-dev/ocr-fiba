from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routes import pipeline, runs
from helpers.image_utils import load_dotenv


def create_app() -> FastAPI:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")

    app = FastAPI(
        title="FIBA OCR Engine API",
        version="0.1.0",
    )
    app.include_router(pipeline.router)
    app.include_router(runs.router)

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
