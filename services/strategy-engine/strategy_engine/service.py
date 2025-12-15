"""Strategy engine main service."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List

import redis.asyncio as aioredis

from .config import StrategyConfig, StrategyEngineSettings
from .loader import load_strategies, unload_strategies
from .models import FeatureSnapshot, StrategySignal

logger = logging.getLogger(__name__)


class StrategyEngineService:
    """Subscribe to feature snapshots and emit strategy signals."""

    def __init__(self, settings: StrategyEngineSettings, redis_client: aioredis.Redis) -> None:
        self.settings = settings
        self.redis = redis_client
        self.strategies = load_strategies(self._ensure_strategies(settings))
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        if not self.strategies:
            logger.warning("No strategies loaded; strategy engine will remain idle")

        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.settings.feature_channel)
        logger.info("Subscribed to feature channel %s", self.settings.feature_channel)

        try:
            while not self._shutdown.is_set():
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    continue

                logger.info("📨 Received message type: %s", message.get("type"))

                payload = message.get("data")
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8")

                logger.info("📦 Processing payload: %s...", str(payload)[:100])
                await self._handle_payload(str(payload))
        finally:
            await pubsub.unsubscribe(self.settings.feature_channel)
            await pubsub.close()
            unload_strategies(self.strategies)

    async def stop(self) -> None:
        self._shutdown.set()

    async def _handle_payload(self, payload: str) -> None:
        try:
            data = json.loads(payload)
            logger.info("✅ Parsed JSON payload successfully")
        except json.JSONDecodeError as exc:
            logger.error("Invalid feature payload: %s", exc)
            return

        if isinstance(data, dict):
            snapshots = [FeatureSnapshot.model_validate(data)]
        else:
            snapshots = [FeatureSnapshot.model_validate(item) for item in data]

        logger.info("📊 Processing %d feature snapshot(s)", len(snapshots))

        signals: List[StrategySignal] = []
        for snapshot in snapshots:
            logger.info("🔍 Evaluating snapshot for %s with %d strategies", snapshot.symbol, len(self.strategies))
            for strategy in self.strategies.values():
                try:
                    signal = strategy.evaluate(snapshot)
                    if signal:
                        logger.info("✨ Strategy %s generated signal for %s", strategy.name, snapshot.symbol)
                        signals.append(signal)
                    else:
                        logger.info("⚪ Strategy %s did not trigger for %s", strategy.name, snapshot.symbol)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Strategy %s failed: %s", strategy.name, exc)

        if signals:
            logger.info("📤 Emitting %d signal(s)", len(signals))
            await self._emit_signals(signals)
        else:
            logger.info("⚠️  No signals generated from this batch")

    async def _emit_signals(self, signals: List[StrategySignal]) -> None:
        for signal in signals:
            try:
                payload = json.dumps(signal.model_dump(mode='json'))
                kwargs = {}
                if self.settings.max_stream_length is not None:
                    kwargs["maxlen"] = self.settings.max_stream_length
                    kwargs["approximate"] = self.settings.approximate_trim
                stream_id = await self.redis.xadd(
                    name=self.settings.signal_stream,
                    fields={"payload": payload},
                    **kwargs,
                )
                logger.info("✅ Emitted signal to %s (ID: %s)", self.settings.signal_stream, stream_id)
            except Exception as exc:
                logger.exception("Failed to emit signal for %s: %s", signal.symbol, exc)

    def _ensure_strategies(self, settings: StrategyEngineSettings) -> List[StrategyConfig]:
        if settings.strategies:
            return settings.strategies

        logger.info("No strategies configured; loading default rapid rise strategy")
        return [
            StrategyConfig(
                name="rapid-rise-default",
                module="strategy_engine.strategies.rapid_rise",
                class_name="RapidRiseStrategy",
                parameters={"min_change": 2.0, "min_volume": 50000},
            )
        ]


async def build_redis_client(settings: StrategyEngineSettings) -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
