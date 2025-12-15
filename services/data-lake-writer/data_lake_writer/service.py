"""Data lake writer service implementation."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import redis.asyncio as aioredis

from .config import LakeWriterSettings
from .models import CleanTickRecord
from .storage import DataLakeStorage

logger = logging.getLogger(__name__)


@dataclass
class FlushState:
    buffer: List[CleanTickRecord]
    last_flush: datetime


class DataLakeWriterService:
    """Consume clean tick stream and persist to data lake."""

    def __init__(self, settings: LakeWriterSettings, redis_client: aioredis.Redis) -> None:
        self.settings = settings
        self.redis = redis_client
        self.storage = DataLakeStorage(settings.output_dir, settings.file_format)
        self._shutdown = asyncio.Event()
        self._flush_state = FlushState(buffer=[], last_flush=datetime.utcnow())

    async def start(self) -> None:
        await self._ensure_consumer_group()
        logger.info(
            "DataLakeWriter started (stream=%s -> dir=%s)",
            self.settings.input_stream,
            self.settings.output_dir,
        )

        while not self._shutdown.is_set():
            try:
                entries = await self._read_batch()
                if entries:
                    for message_id, payload in entries:
                        await self._handle_message(message_id, payload)
                await self._maybe_flush()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("DataLakeWriter loop error: %s", exc)
                await asyncio.sleep(1)

        await self._flush(force=True)
        logger.info("DataLakeWriter stopped")

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

    async def _handle_message(self, message_id: str, payload: Dict[str, str]) -> None:
        raw_json = payload.get("payload")
        if raw_json is None:
            await self._ack(message_id)
            return

        try:
            data = json.loads(raw_json)
            record = CleanTickRecord.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to parse tick for data lake: %s", exc)
            await self._ack(message_id)
            return

        self._flush_state.buffer.append(record)
        await self._ack(message_id)

        if len(self._flush_state.buffer) >= self.settings.max_buffer_size:
            await self._flush(force=True)

    async def _maybe_flush(self) -> None:
        elapsed = (datetime.utcnow() - self._flush_state.last_flush).total_seconds()
        if elapsed >= self.settings.flush_interval_seconds and self._flush_state.buffer:
            await self._flush(force=True)

    async def _flush(self, force: bool = False) -> None:
        if not self._flush_state.buffer:
            return

        try:
            shard = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            path = self.storage.write_batch(self._flush_state.buffer, shard)
            logger.info("Written %d records to %s", len(self._flush_state.buffer), path)
        finally:
            self._flush_state.buffer.clear()
            self._flush_state.last_flush = datetime.utcnow()

    async def _ack(self, message_id: str) -> None:
        await self.redis.xack(
            self.settings.input_stream,
            self.settings.consumer_group,
            message_id,
        )


async def build_redis_client(settings: LakeWriterSettings) -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
