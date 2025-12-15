"""Backtest service FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from .routes import backtests


def create_app() -> FastAPI:
    app = FastAPI(title="Backtest Service", version="1.0.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(backtests.router)
    return app
