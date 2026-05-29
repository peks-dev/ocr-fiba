from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

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

    return app


app = create_app()
