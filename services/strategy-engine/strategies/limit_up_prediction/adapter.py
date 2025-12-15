"""Adapter for integrating limit_up_prediction strategy into strategy-engine."""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from strategy_engine.strategies.base import Strategy
from strategy_engine.models import FeatureSnapshot, StrategySignal

from .strategy import LimitUpPredictionStrategy

logger = logging.getLogger(__name__)


class LimitUpPredictionStrategyAdapter(Strategy):
    """
    Adapter that wraps LimitUpPredictionStrategy for strategy-engine.
    """

    def __init__(self, name: str, **parameters) -> None:
        super().__init__(name, **parameters)

        # Create config for underlying strategy
        config = {
            'parameters': parameters,
            'risk_controls': {
                'min_confidence': parameters.get('min_confidence', 0.50),
                'blacklist_sectors': parameters.get('blacklist_sectors', ['ST', '退市', '*ST']),
                'max_distance_to_limit': parameters.get('max_distance_to_limit', 8.0)
            }
        }

        self.strategy = LimitUpPredictionStrategy(config)
        logger.info(f"LimitUpPredictionStrategyAdapter initialized with config: {config}")

    def evaluate(self, feature: FeatureSnapshot) -> Optional[StrategySignal]:
        """
        Evaluate feature snapshot and return strategy signal.
        """
        # Convert FeatureSnapshot to dict format expected by strategy
        snapshot_dict = self._feature_to_snapshot(feature)

        # Call the strategy's analyze method
        signals = self.strategy.analyze_sync(snapshot_dict)

        if not signals:
            return None

        # Return the first (and only) signal
        return self._signal_to_strategy_signal(signals[0])

    def _feature_to_snapshot(self, feature: FeatureSnapshot) -> Dict[str, Any]:
        """Convert FeatureSnapshot to snapshot dict format."""
        return {
            'symbol': feature.symbol,
            'price': feature.price,
            'price_change_rate': feature.change_percent / 100 if feature.change_percent else 0,
            'volume': feature.volume_sum,
            'volume_ratio': feature.volume_sum / max(feature.avg_price * 100, 1),  # Estimate
            'turnover_rate': feature.turnover_sum / (feature.price * feature.volume_sum) if feature.volume_sum > 0 else 0,
            'avg_price': feature.avg_price,
            'change_speed': feature.change_percent / 100 if feature.change_percent else 0,
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
            window=signal.get('window', '5s'),
            metadata=signal.get('metadata', {}),
            triggered_at=signal.get('triggered_at')
        )

    def on_load(self) -> None:
        """Hook called when strategy is loaded."""
        logger.info(f"LimitUpPredictionStrategyAdapter '{self.name}' loaded successfully")

    def on_unload(self) -> None:
        """Hook called when strategy is unloaded."""
        logger.info(f"LimitUpPredictionStrategyAdapter '{self.name}' unloaded")
