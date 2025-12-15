"""Opportunity aggregator service."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Dict, List, Tuple

import redis.asyncio as aioredis

from .config import AggregatorSettings
from .models import Opportunity, OpportunityState, StrategySignal
from .state import OpportunityManager

logger = logging.getLogger(__name__)


class OpportunityAggregatorService:
    """Aggregate strategy signals into opportunities."""

    def __init__(self, settings: AggregatorSettings, redis_client: aioredis.Redis) -> None:
        self.settings = settings
        self.redis = redis_client
        self.manager = OpportunityManager(expiration=timedelta(seconds=settings.tracking_expiration_seconds))
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        await self._ensure_consumer_group()
        logger.info("Opportunity aggregator started (stream=%s)", self.settings.signal_stream)

        while not self._shutdown.is_set():
            try:
                entries = await self._read_batch()
                if entries:
                    for message_id, payload in entries:
                        await self._process_message(message_id, payload)
                await self._publish_closed()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("Aggregator loop error: %s", exc)
                await asyncio.sleep(1)

    async def stop(self) -> None:
        self._shutdown.set()

    async def _ensure_consumer_group(self) -> None:
        try:
            await self.redis.xgroup_create(
                name=self.settings.signal_stream,
                groupname=self.settings.consumer_group,
                id="0",
                mkstream=True,
            )
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def _read_batch(self) -> List[Tuple[str, Dict[str, str]]]:
        result = await self.redis.xreadgroup(
            groupname=self.settings.consumer_group,
            consumername=self.settings.consumer_name,
            streams={self.settings.signal_stream: ">"},
            count=self.settings.read_count,
            block=self.settings.block_ms,
        )

        entries: List[Tuple[str, Dict[str, str]]] = []
        if not result:
            return entries
        for _stream, messages in result:
            entries.extend(messages)
        return entries

    async def _process_message(self, message_id: str, payload: Dict[str, str]) -> None:
        raw_json = payload.get("payload")
        if raw_json is None:
            await self._ack(message_id)
            return

        try:
            data = json.loads(raw_json)
            signal = StrategySignal.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to parse strategy signal: %s", exc)
            await self._ack(message_id)
            return

        opportunity = self.manager.ingest(signal)
        await self._publish_opportunity(opportunity)
        await self._ack(message_id)

    async def _publish_opportunity(self, opportunity: Opportunity) -> None:
        payload = opportunity.model_dump_json()
        kwargs = {}
        if self.settings.max_stream_length is not None:
            kwargs["maxlen"] = self.settings.max_stream_length
            kwargs["approximate"] = self.settings.approximate_trim
        await self.redis.xadd(
            name=self.settings.opportunity_stream,
            fields={"payload": payload},
            **kwargs,
        )

        if self.settings.opportunity_channel:
            message = json.dumps({
                "type": "opportunity",
                "payload": json.loads(payload)
            })
            await self.redis.publish(self.settings.opportunity_channel, message)

    async def _publish_closed(self) -> None:
        closed = self.manager.cleanup()
        for opportunity in closed:
            await self._publish_opportunity(opportunity)

    async def _ack(self, message_id: str) -> None:
        await self.redis.xack(
            self.settings.signal_stream,
            self.settings.consumer_group,
            message_id,
        )


async def build_redis_client(settings: AggregatorSettings) -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
