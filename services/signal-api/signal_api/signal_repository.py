"""Repository for retrieving strategy signals from Redis streams."""

from __future__ import annotations

import json
from collections import Counter
from typing import List, Optional

import redis.asyncio as aioredis

from .models import StrategySignalResponse


class SignalRepository:
    """Repository for accessing dfp:strategy_signals Redis stream."""

    def __init__(self, redis_client: aioredis.Redis, stream: str = "dfp:strategy_signals", max_records: int = 1000) -> None:
        self.redis = redis_client
        self.stream = stream
        self.max_records = max_records

    async def list_signals(
        self,
        limit: Optional[int] = None,
        strategy: Optional[str] = None,
        symbol: Optional[str] = None,
        signal_type: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[StrategySignalResponse]:
        """
        List signals with optional filtering.

        Args:
            limit: Maximum number of signals to return
            strategy: Filter by strategy name (e.g., 'anomaly_detection', 'limit_up_prediction')
            symbol: Filter by stock symbol (e.g., 'sh600000')
            signal_type: Filter by signal type (e.g., 'volume_surge', 'limit_up_potential')
            min_confidence: Minimum confidence threshold (0.0 to 1.0)

        Returns:
            List of strategy signals matching the filters
        """
        limit = min(limit or self.max_records, self.max_records)

        # Fetch from Redis stream (reverse order - newest first)
        result = await self.redis.xrevrange(self.stream, count=limit * 2)  # Fetch extra for filtering

        signals: List[StrategySignalResponse] = []

        for message_id, payload in result:
            data = payload.get("payload")
            if not data:
                continue

            try:
                obj = json.loads(data)

                # Apply filters
                if strategy and obj.get("strategy") != strategy:
                    continue

                if symbol and obj.get("symbol") != symbol:
                    continue

                if signal_type and obj.get("signal_type") != signal_type:
                    continue

                if min_confidence is not None and obj.get("confidence", 0) < min_confidence:
                    continue

                # Parse and add to results
                signal = StrategySignalResponse.model_validate(obj)
                signals.append(signal)

                # Stop if we have enough
                if len(signals) >= limit:
                    break

            except Exception as e:
                # Log but don't fail on invalid data
                continue

        return signals

    async def get_signal_stats(self) -> dict:
        """
        Get statistics about recent signals.

        Returns:
            Dictionary with signal counts, strategies, types, etc.
        """
        # Fetch recent signals
        result = await self.redis.xrevrange(self.stream, count=500)

        strategy_counts = Counter()
        signal_type_counts = Counter()
        symbol_counts = Counter()
        total_signals = 0
        total_confidence = 0.0

        for message_id, payload in result:
            data = payload.get("payload")
            if not data:
                continue

            try:
                obj = json.loads(data)
                total_signals += 1

                strategy_counts[obj.get("strategy", "unknown")] += 1
                signal_type_counts[obj.get("signal_type", "unknown")] += 1
                symbol_counts[obj.get("symbol", "unknown")] += 1
                total_confidence += obj.get("confidence", 0)

            except Exception:
                continue

        avg_confidence = total_confidence / total_signals if total_signals > 0 else 0

        return {
            "total_signals": total_signals,
            "average_confidence": round(avg_confidence, 3),
            "strategies": dict(strategy_counts.most_common(10)),
            "signal_types": dict(signal_type_counts.most_common(10)),
            "top_symbols": dict(symbol_counts.most_common(20)),
        }
