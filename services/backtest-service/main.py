"""Entry point for backtest service."""

from __future__ import annotations

import logging

import uvicorn

from backtest_service.app import create_app
from backtest_service.config import get_settings


def run() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8200, log_level=settings.log_level.lower())


if __name__ == "__main__":
    run()
