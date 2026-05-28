from __future__ import annotations

from fastapi import FastAPI

from api.routes import pipeline, runs


def create_app() -> FastAPI:
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
