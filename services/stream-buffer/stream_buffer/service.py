"""Stream buffer replication service."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import redis.asyncio as aioredis

from .config import BufferSettings, StreamPipelineConfig, TargetStreamConfig

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    """Runtime metrics for a single replication pipeline."""

    name: str
    last_id: str
    processed_messages: int = 0
    replicated_messages: int = 0
    last_processed_at: datetime | None = None
    last_error: str | None = None

    def as_dict(self) -> Dict[str, object]:
        return {
            "pipeline": self.name,
            "last_id": self.last_id,
            "processed_messages": self.processed_messages,
            "replicated_messages": self.replicated_messages,
            "last_processed_at": self.last_processed_at.isoformat() if self.last_processed_at else None,
            "last_error": self.last_error,
        }


class StreamBufferService:
    """Replicates Redis Streams according to configuration."""

    def __init__(self, settings: BufferSettings, redis_client: aioredis.Redis) -> None:
        self.settings = settings
        self.redis = redis_client
        self._shutdown = asyncio.Event()
        self._tasks: Dict[str, asyncio.Task[None]] = {}
        self._metrics: Dict[str, PipelineMetrics] = {}

    async def start(self) -> None:
        if not self.settings.pipelines:
            logger.warning("No pipelines configured for StreamBufferService")
            await self._shutdown.wait()
            return

        for pipeline in self.settings.pipelines:
            metrics = PipelineMetrics(name=pipeline.name, last_id=pipeline.start_from)
            self._metrics[pipeline.name] = metrics
            task = asyncio.create_task(self._run_pipeline(pipeline, metrics))
            self._tasks[pipeline.name] = task

        await self._shutdown.wait()

    async def stop(self) -> None:
        self._shutdown.set()
        for name, task in list(self._tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug("Pipeline %s cancelled", name)
            finally:
                self._tasks.pop(name, None)

    async def _run_pipeline(self, pipeline: StreamPipelineConfig, metrics: PipelineMetrics) -> None:
        last_id = pipeline.start_from
        logger.info(
            "Starting pipeline %s (source=%s, targets=%d)",
            pipeline.name,
            pipeline.source_stream,
            len(pipeline.targets),
        )

        while not self._shutdown.is_set():
            try:
                result = await self.redis.xread(
                    streams={pipeline.source_stream: last_id},
                    count=pipeline.batch_size,
                    block=pipeline.block_ms,
                )

                if not result:
                    continue

                for _stream, entries in result:
                    await self._handle_entries(pipeline, entries, metrics)
                    if entries:
                        last_id = entries[-1][0]
                        metrics.last_id = last_id

                if pipeline.trim_source_to:
                    await self.redis.xtrim(
                        name=pipeline.source_stream,
                        maxlen=pipeline.trim_source_to,
                        approximate=True,
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("Pipeline %s failed: %s", pipeline.name, exc)
                metrics.last_error = str(exc)
                await asyncio.sleep(1)

        logger.info("Pipeline %s stopped", pipeline.name)

    async def _handle_entries(
        self,
        pipeline: StreamPipelineConfig,
        entries: List[Tuple[str, Dict[str, str]]],
        metrics: PipelineMetrics,
    ) -> None:
        for message_id, payload in entries:
            metrics.processed_messages += 1
            metrics.last_processed_at = datetime.utcnow()

            await self._replicate_to_targets(pipeline.targets, payload)
            metrics.replicated_messages += len(pipeline.targets)

    async def _replicate_to_targets(
        self,
        targets: List[TargetStreamConfig],
        payload: Dict[str, str],
    ) -> None:
        for target in targets:
            kwargs = {}
            if target.max_length is not None:
                kwargs["maxlen"] = target.max_length
                kwargs["approximate"] = target.approximate
            await self.redis.xadd(name=target.name, fields=payload, **kwargs)

    def metrics(self) -> List[Dict[str, object]]:
        """Return collected pipeline metrics."""

        return [metric.as_dict() for metric in self._metrics.values()]


async def build_redis_client(settings: BufferSettings) -> aioredis.Redis:
    """Factory for redis client instances."""

    return aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
