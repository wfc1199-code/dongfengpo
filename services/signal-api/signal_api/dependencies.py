"""Dependency providers for FastAPI."""

from __future__ import annotations

from functools import lru_cache

import redis.asyncio as aioredis

from .config import SignalApiSettings, get_settings
from .repository import OpportunityRepository


@lru_cache()
def get_redis_client() -> aioredis.Redis:
    settings = get_settings()
    return aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


def get_repository() -> OpportunityRepository:
    settings = get_settings()
    redis_client = get_redis_client()
    return OpportunityRepository(redis_client, settings.opportunity_stream, settings.max_records)


def get_signal_repository() -> SignalRepository:
    """Dependency for SignalRepository."""
    from .signal_repository import SignalRepository
    settings = get_settings()
    redis_client = get_redis_client()
    return SignalRepository(redis_client, "dfp:strategy_signals", settings.max_records)
