"""Rapid rise strategy implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..models import FeatureSnapshot, StrategySignal
from .base import Strategy


class RapidRiseStrategy(Strategy):
    """Detect rapid price increases within a window."""

    def __init__(self, name: str, *, min_change: float = 2.0, min_volume: int = 100000, **kwargs) -> None:
        super().__init__(name, min_change=min_change, min_volume=min_volume, **kwargs)
        self.min_change = min_change
        self.min_volume = min_volume

    def evaluate(self, feature: FeatureSnapshot) -> Optional[StrategySignal]:
        change_percent = feature.change_percent or 0.0
        if change_percent < self.min_change:
            return None

        if feature.volume_sum < self.min_volume:
            return None

        confidence = min(0.5 + change_percent / 10, 0.95)
        strength = min(change_percent * 10 + feature.volume_sum / self.min_volume * 10, 100)
        reasons = [
            f"涨幅 {change_percent:.2f}%",
            f"成交量 {feature.volume_sum}" ,
        ]

        return StrategySignal(
            strategy=self.name,
            symbol=feature.symbol,
            signal_type="rapid_rise",
            confidence=confidence,
            strength_score=strength,
            reasons=reasons,
            triggered_at=datetime.utcnow(),
            window=feature.window,
            metadata={
                "price": feature.price,
                "avg_price": feature.avg_price,
            },
        )
