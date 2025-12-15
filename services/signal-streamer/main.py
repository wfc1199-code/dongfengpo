"""Entry point for signal streamer service."""

from __future__ import annotations

import logging

import uvicorn
import redis.asyncio as aioredis

from signal_streamer.config import SignalStreamerSettings, get_settings
from signal_streamer.server import OpportunityStreamer, create_app


def run() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    redis_client = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    streamer = OpportunityStreamer(settings=settings, redis_client=redis_client)
    app = create_app(streamer)

    uvicorn.run(app, host="0.0.0.0", port=8002, log_level=settings.log_level.lower())


if __name__ == "__main__":
    run()
