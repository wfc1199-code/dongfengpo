"""Collector Gateway service orchestrating data source adapters."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, Iterable, List, MutableMapping

import redis.asyncio as aioredis

from data_contracts import TickRecord

from .adapters.base import AdapterTick, DataSourceAdapter
from .config import CollectorSettings

logger = logging.getLogger(__name__)


class CollectorService:
    """Main coordinator for streaming ticks into Redis Streams."""

    def __init__(
        self,
        settings: CollectorSettings,
        redis_client: aioredis.Redis,
        adapters: Iterable[DataSourceAdapter],
    ) -> None:
        self.settings = settings
        self.redis = redis_client
        self.adapters: Dict[str, DataSourceAdapter] = {
            adapter.name: adapter for adapter in adapters
        }
        self._tasks: MutableMapping[str, asyncio.Task[None]] = {}
        self._shutdown = asyncio.Event()

    async def start(self, symbols: List[str]) -> None:
        """Start streaming from all enabled adapters."""

        logger.info("Starting collector service with %d adapters", len(self.adapters))
        for name, adapter in self.adapters.items():
            task = asyncio.create_task(self._pump_adapter(name, adapter, symbols))
            self._tasks[name] = task

    async def stop(self) -> None:
        """Stop all running tasks and adapters."""

        logger.info("Stopping collector service")
        self._shutdown.set()
        for name, task in list(self._tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug("Adapter task %s cancelled", name)
            finally:
                self._tasks.pop(name, None)

        await asyncio.gather(*(adapter.stop() for adapter in self.adapters.values()), return_exceptions=True)

    async def _pump_adapter(
        self, name: str, adapter: DataSourceAdapter, symbols: List[str]
    ) -> None:
        """Stream data from an adapter and push into Redis."""

        try:
            await adapter.start()
            async for tick in adapter.stream(symbols):
                if self._shutdown.is_set():
                    break
                await self._write_tick(name, tick)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Adapter %s failed: %s", name, exc)
        finally:
            await adapter.stop()
            logger.info("Adapter %s stopped", name)

    async def _write_tick(self, source: str, tick: AdapterTick) -> None:
        """Serialize tick and append to Redis Stream."""

        record = TickRecord(
            source=source,
            symbol=tick.symbol,
            price=tick.price,
            volume=tick.volume,
            turnover=tick.turnover,
            bid_price=tick.bid_price,
            bid_volume=tick.bid_volume,
            ask_price=tick.ask_price,
            ask_volume=tick.ask_volume,
            timestamp=tick.timestamp,
            ingested_at=datetime.utcnow(),
            raw=tick.raw,
        )
        payload = record.model_dump_json()

        await self.redis.xadd(
            self.settings.stream_name,
            {"payload": payload},
            maxlen=None,
            approximate=False,
        )


async def build_redis_client(settings: CollectorSettings) -> aioredis.Redis:
    """Factory for Redis client used by the service."""

    return aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
