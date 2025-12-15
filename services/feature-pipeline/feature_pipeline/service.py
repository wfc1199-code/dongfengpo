"""Feature pipeline service implementation."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Dict, List, Tuple

import redis.asyncio as aioredis

from .calculators import FeatureCalculator
from .config import FeaturePipelineSettings
from .models import CleanTick

logger = logging.getLogger(__name__)


class FeaturePipelineService:
    """Consume clean ticks and publish feature snapshots."""

    def __init__(self, settings: FeaturePipelineSettings, redis_client: aioredis.Redis) -> None:
        self.settings = settings
        self.redis = redis_client
        window_configs = self._build_window_config(settings)
        self.calculator = FeatureCalculator(window_configs)
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        await self._ensure_consumer_group()
        logger.info(
            "Feature pipeline started (stream=%s channel=%s)",
            self.settings.input_stream,
            self.settings.publish_channel,
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
                logger.exception("Feature pipeline loop error: %s", exc)

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
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def _read_batch(self) -> List[Tuple[str, Dict[str, str]]]:
        result = await self.redis.xreadgroup(
            groupname=self.settings.consumer_group,
            consumername=self.settings.consumer_name,
            streams={self.settings.input_stream: ">"},
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
            tick_dict = json.loads(raw_json)
            tick = CleanTick.model_validate(tick_dict)
            logger.info("Processing tick %s: %s @ %s", message_id, tick.symbol, tick.price)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to parse clean tick: %s", exc)
            await self._ack(message_id)
            return

        snapshots = self.calculator.update(tick)
        logger.info("Generated %d feature snapshots for %s", len(snapshots), tick.symbol)
        await self._publish(snapshots)
        logger.info("Published %d snapshots to %s", len(snapshots), self.settings.publish_channel)
        await self._ack(message_id)

    async def _publish(self, snapshots) -> None:  # noqa: ANN001 - snapshots is list of FeatureSnapshot
        if not snapshots:
            return
        payload = json.dumps([snapshot.model_dump(mode='json') for snapshot in snapshots])
        await self.redis.publish(self.settings.publish_channel, payload)

    async def _ack(self, message_id: str) -> None:
        await self.redis.xack(
            self.settings.input_stream,
            self.settings.consumer_group,
            message_id,
        )

    def _build_window_config(self, settings: FeaturePipelineSettings) -> Dict[str, timedelta]:
        window_configs: Dict[str, timedelta] = {}
        for window in settings.windows:
            if window.window_unit == "seconds":
                duration = timedelta(seconds=window.window_size)
            else:
                duration = timedelta(minutes=window.window_size)
            window_configs[window.name] = duration
        return window_configs


async def build_redis_client(settings: FeaturePipelineSettings) -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
