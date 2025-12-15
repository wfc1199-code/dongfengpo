"""Cached adapter wrapper with Redis support."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import AsyncIterator, Iterable, Optional

import redis.asyncio as aioredis

from .base import AdapterTick, DataSourceAdapter

logger = logging.getLogger(__name__)


class CachedAdapter(DataSourceAdapter):
    """
    Wrapper that adds Redis caching layer to any data source adapter.

    This reduces API calls and improves performance by caching recent ticks.
    """

    def __init__(
        self,
        wrapped_adapter: DataSourceAdapter,
        redis_client: aioredis.Redis,
        cache_ttl_seconds: int = 60,
        cache_key_prefix: str = "dfp:tick_cache"
    ):
        super().__init__(f"cached_{wrapped_adapter.name}")
        self.wrapped = wrapped_adapter
        self.redis = redis_client
        self.cache_ttl = cache_ttl_seconds
        self.key_prefix = cache_key_prefix

        logger.info(
            f"CachedAdapter wrapping {wrapped_adapter.name} "
            f"with {cache_ttl_seconds}s TTL"
        )

    async def start(self) -> None:
        """Start the wrapped adapter."""
        await self.wrapped.start()

    async def stop(self) -> None:
        """Stop the wrapped adapter."""
        await self.wrapped.stop()

    async def stream(self, symbols: Iterable[str]) -> AsyncIterator[AdapterTick]:
        """
        Stream ticks with caching.

        Checks cache first, falls back to wrapped adapter on miss.
        """
        async for tick in self.wrapped.stream(symbols):
            # Cache the tick
            await self._cache_tick(tick)
            yield tick

    async def fetch_snapshot(self, symbol: str) -> AdapterTick:
        """
        Fetch snapshot with caching.

        Returns cached data if fresh, otherwise fetches from wrapped adapter.
        """
        # Try cache first
        cached = await self._get_cached_tick(symbol)
        if cached:
            logger.debug(f"Cache hit for {symbol}")
            return cached

        # Cache miss - fetch from wrapped adapter
        logger.debug(f"Cache miss for {symbol}, fetching from {self.wrapped.name}")
        tick = await self.wrapped.fetch_snapshot(symbol)

        # Cache the result
        await self._cache_tick(tick)

        return tick

    async def _cache_tick(self, tick: AdapterTick) -> None:
        """Store tick in Redis cache."""
        try:
            cache_key = f"{self.key_prefix}:{tick.symbol}"

            # Serialize tick to JSON
            tick_data = {
                'symbol': tick.symbol,
                'price': tick.price,
                'volume': tick.volume,
                'turnover': tick.turnover,
                'bid_price': tick.bid_price,
                'bid_volume': tick.bid_volume,
                'ask_price': tick.ask_price,
                'ask_volume': tick.ask_volume,
                'timestamp': tick.timestamp.isoformat(),
                'source': self.wrapped.name
            }

            # Store with TTL
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(tick_data)
            )

        except Exception as e:
            logger.warning(f"Failed to cache tick for {tick.symbol}: {e}")

    async def _get_cached_tick(self, symbol: str) -> Optional[AdapterTick]:
        """Retrieve tick from Redis cache."""
        try:
            cache_key = f"{self.key_prefix}:{symbol}"
            cached_data = await self.redis.get(cache_key)

            if not cached_data:
                return None

            # Deserialize from JSON
            tick_data = json.loads(cached_data)

            return AdapterTick(
                symbol=tick_data['symbol'],
                price=float(tick_data['price']),
                volume=int(tick_data['volume']),
                turnover=float(tick_data['turnover']),
                bid_price=tick_data.get('bid_price'),
                bid_volume=tick_data.get('bid_volume'),
                ask_price=tick_data.get('ask_price'),
                ask_volume=tick_data.get('ask_volume'),
                timestamp=datetime.fromisoformat(tick_data['timestamp']),
                raw={'cached': True, 'source': tick_data.get('source')}
            )

        except Exception as e:
            logger.warning(f"Failed to get cached tick for {symbol}: {e}")
            return None
