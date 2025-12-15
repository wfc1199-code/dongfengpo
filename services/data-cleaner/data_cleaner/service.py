"""Implementation of the data cleaner stream service."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Tuple

import redis.asyncio as aioredis

from .config import CleanerSettings
from .models import CleanTick, RawTick
from .transformer import clean_tick

logger = logging.getLogger(__name__)


class DataCleanerService:
    """Consume raw ticks and emit cleaned payloads."""

    def __init__(self, settings: CleanerSettings, redis_client: aioredis.Redis) -> None:
        self.settings = settings
        self.redis = redis_client
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        await self._ensure_consumer_group()
        logger.info(
            "DataCleanerService started (stream=%s group=%s consumer=%s)",
            self.settings.input_stream,
            self.settings.consumer_group,
            self.settings.consumer_name,
        )

        while not self._shutdown.is_set():
            try:
                entries = await self._read_batch()
                if not entries:
                    continue

                for message_id, payload in entries:
                    await self._process_message(message_id, payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("Cleaner loop error: %s", exc)

        logger.info("DataCleanerService shutting down")

    async def stop(self) -> None:
        self._shutdown.set()

    async def _ensure_consumer_group(self) -> None:
        try:
            await self.redis.xgroup_create(
                name=self.settings.input_stream,
                groupname=self.settings.consumer_group,
                id="0",
                mkstream=True,
            )
            logger.info(
                "Created consumer group %s on %s",
                self.settings.consumer_group,
                self.settings.input_stream,
            )
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                logger.debug("Consumer group already exists")
            else:
                raise

    async def _read_batch(self) -> List[Tuple[str, Dict[str, Any]]]:
        result = await self.redis.xreadgroup(
            groupname=self.settings.consumer_group,
            consumername=self.settings.consumer_name,
            streams={self.settings.input_stream: ">"},
            count=self.settings.read_count,
            block=self.settings.block_ms,
        )

        entries: List[Tuple[str, Dict[str, Any]]] = []
        if not result:
            return entries

        for _stream_name, messages in result:
            for message_id, payload in messages:
                entries.append((message_id, payload))
        return entries

    async def _process_message(self, message_id: str, payload: Dict[str, Any]) -> None:
        raw_json = payload.get("payload")
        if raw_json is None:
            logger.warning("Received message without payload: %s", payload)
            await self._ack(message_id)
            return

        try:
            raw_dict = json.loads(raw_json)
            raw_tick = RawTick.model_validate(raw_dict)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to parse raw tick: %s", exc)
            await self._ack(message_id)
            return

        cleaned = clean_tick(raw_tick)
        await self._publish(cleaned)
        await self._ack(message_id)

    async def _publish(self, tick: CleanTick) -> None:
        # 使用model_dump_json直接生成JSON字符串,自动处理datetime序列化
        payload = tick.model_dump_json()
        kwargs = {}
        if self.settings.max_output_len is not None:
            kwargs["maxlen"] = self.settings.max_output_len
            kwargs["approximate"] = self.settings.approximate_trim

        await self.redis.xadd(
            name=self.settings.output_stream,
            fields={"payload": payload},
            **kwargs,
        )

    async def _ack(self, message_id: str) -> None:
        await self.redis.xack(
            self.settings.input_stream,
            self.settings.consumer_group,
            message_id,
        )


async def build_redis_client(settings: CleanerSettings) -> aioredis.Redis:
    """Factory function for redis client instances."""

    return aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
