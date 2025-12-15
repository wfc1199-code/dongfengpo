"""Adapter for integrating anomaly_detection strategy into strategy-engine."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, Optional

from strategy_engine.strategies.base import Strategy
from strategy_engine.models import FeatureSnapshot, StrategySignal

from .strategy import AnomalyDetectionStrategy

logger = logging.getLogger(__name__)


class AnomalyDetectionStrategyAdapter(Strategy):
    """
    Adapter that wraps AnomalyDetectionStrategy for strategy-engine.

    Converts between:
    - FeatureSnapshot (strategy-engine format) → Dict (strategy format)
    - List[Dict] (strategy signals) → StrategySignal (strategy-engine format)
    """

    def __init__(self, name: str, **parameters) -> None:
        super().__init__(name, **parameters)

        # Create config for underlying strategy
        config = {
            'parameters': parameters,
            'risk_controls': {
                'min_confidence': parameters.get('min_confidence', 0.60),
                'blacklist_sectors': parameters.get('blacklist_sectors', ['ST', '退市'])
            }
        }

        self.strategy = AnomalyDetectionStrategy(config)
        logger.info(f"AnomalyDetectionStrategyAdapter initialized with config: {config}")

    def evaluate(self, feature: FeatureSnapshot) -> Optional[StrategySignal]:
        """
        Evaluate feature snapshot and return strategy signal.

        This is the synchronous interface required by strategy-engine.
        """
        # Convert FeatureSnapshot to dict format expected by strategy
        snapshot_dict = self._feature_to_snapshot(feature)

        # Call the strategy's analyze method directly (making it sync)
        signals = self.strategy.analyze_sync(snapshot_dict)

        if not signals:
            return None

        # Return the highest confidence signal
        best_signal = max(signals, key=lambda s: s['confidence'])
        return self._signal_to_strategy_signal(best_signal)

    def _feature_to_snapshot(self, feature: FeatureSnapshot) -> Dict[str, Any]:
        """Convert FeatureSnapshot to snapshot dict format."""
        # FeatureSnapshot has direct attributes, not a nested features dict
        return {
            'symbol': feature.symbol,
            'price': feature.price,
            'price_change_rate': feature.change_percent / 100 if feature.change_percent else 0,  # Convert % to ratio
            'volume': feature.volume_sum,
            'volume_ratio': feature.volume_sum / max(feature.avg_price * 100, 1),  # Estimate
            'turnover_rate': feature.turnover_sum / (feature.price * feature.volume_sum) if feature.volume_sum > 0 else 0,
            'avg_price': feature.avg_price,
            'change_speed': feature.change_percent / 100 if feature.change_percent else 0,  # Use change_percent as proxy
            'window': feature.window
        }

    def _signal_to_strategy_signal(self, signal: Dict[str, Any]) -> StrategySignal:
        """Convert strategy signal dict to StrategySignal model."""
        return StrategySignal(
            strategy=self.name,
            symbol=signal['symbol'],
            signal_type=signal['signal_type'],
            confidence=signal['confidence'],
            strength_score=signal['strength_score'],
            reasons=signal['reasons'],
            window=signal.get('window', '5s'),  # Add window field
            metadata=signal.get('metadata', {}),
            triggered_at=signal.get('triggered_at')
        )

    def on_load(self) -> None:
        """Hook called when strategy is loaded."""
        logger.info(f"AnomalyDetectionStrategyAdapter '{self.name}' loaded successfully")

    def on_unload(self) -> None:
        """Hook called when strategy is unloaded."""
        logger.info(f"AnomalyDetectionStrategyAdapter '{self.name}' unloaded")
