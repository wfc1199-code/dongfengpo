"""Entry point for the signal API service."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import asynccontextmanager

import uvicorn

from signal_api.app import create_app
from signal_api.config import SignalApiSettings, get_settings
from signal_api.dependencies import get_redis_client


@asynccontextmanager
async def lifespan(app):  # type: ignore[override]
    # Startup
    settings: SignalApiSettings = get_settings()
    logging.basicConfig(level=settings.log_level)
    redis_client = get_redis_client()

    yield

    # Shutdown
    await redis_client.close()


def run() -> None:
    settings = get_settings()
    
    # Use create_app() with lifespan for startup/shutdown
    app = create_app(lifespan=lifespan)

    uvicorn.run(app, host="0.0.0.0", port=9001, log_level=settings.log_level.lower())


if __name__ == "__main__":
    run()
