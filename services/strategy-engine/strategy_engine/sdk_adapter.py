"""Adapter to integrate dongfengpo-strategy-sdk with strategy-engine."""

from __future__ import annotations

from typing import Optional

from strategy_sdk import BaseStrategy, Signal, SignalType, StrategyRegistry

from .models import FeatureSnapshot, StrategySignal
from .strategies.base import Strategy


class SDKStrategyAdapter(Strategy):
    """Adapter to wrap SDK BaseStrategy for use in strategy-engine."""

    def __init__(self, sdk_strategy: BaseStrategy, name: str, **parameters) -> None:
        super().__init__(name=name, **parameters)
        self.sdk_strategy = sdk_strategy

    def evaluate(self, feature: FeatureSnapshot) -> Optional[StrategySignal]:
        """Evaluate using SDK strategy and convert to engine signal."""
        import asyncio
        import logging

        logger = logging.getLogger(__name__)

        # Convert FeatureSnapshot to SDK's expected format
        # SDK strategies expect different field names matching market data
        market_data = {
            "code": feature.symbol,
            "name": feature.symbol,  # Use symbol as name for now
            "price": feature.price,
            "price_change_rate": getattr(feature, "change_percent", 0.0) / 100.0 if hasattr(feature, "change_percent") and feature.change_percent else 0.0,
            "volume": getattr(feature, "volume_sum", 0),
            "volume_ratio": 2.5,  # Mock value - would come from real-time features
            "money_flow_5min": 10000000,  # Mock value - would come from real-time features
            "turnover_rate": 3.0,  # Mock value - would come from real-time features
            "timestamp": feature.timestamp.isoformat() if hasattr(feature.timestamp, 'isoformat') else str(feature.timestamp),
        }

        # Execute async SDK strategy in a new event loop
        # This is necessary because strategy-engine's evaluate() is synchronous
        # but SDK strategies are async
        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context but evaluate() is called synchronously
                # This shouldn't happen in normal operation
                logger.warning("Unexpected: evaluate() called within running event loop")
                return None
            except RuntimeError:
                # No running loop - this is the expected case
                # Create a new event loop for this synchronous call
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Run the async analyze() method
                    sdk_signals = loop.run_until_complete(self.sdk_strategy.analyze(market_data))
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)

            # Check if we got any signals
            if not sdk_signals or len(sdk_signals) == 0:
                return None

            # Take the first signal (SDK strategies return a list)
            sdk_signal = sdk_signals[0]

            # Convert SDK Signal to StrategySignal
            # Map SDK signal fields to engine signal fields
            return StrategySignal(
                strategy=self.name,  # 'strategy' not 'strategy_name'
                symbol=feature.symbol,
                signal_type=self._convert_signal_type(sdk_signal.type),
                confidence=sdk_signal.confidence,
                strength_score=sdk_signal.confidence,  # Use confidence as strength
                reasons=[sdk_signal.reason] if hasattr(sdk_signal, 'reason') and sdk_signal.reason else [],
                triggered_at=feature.timestamp,  # 'triggered_at' not 'timestamp'
                window=feature.window,  # Pass through the window from feature
                metadata=sdk_signal.metadata if hasattr(sdk_signal, 'metadata') else {},
            )

        except Exception as e:
            # Log error and return None (no signal generated)
            logger.error(f"Error evaluating SDK strategy {self.name}: {e}", exc_info=True)
            return None

    def _convert_signal_type(self, sdk_type: SignalType) -> str:
        """Convert SDK SignalType to string."""
        return sdk_type.value

    def on_load(self) -> None:
        """Hook called when strategy is loaded."""
        import asyncio
        import logging

        logger = logging.getLogger(__name__)

        # SDK strategies need to be initialized with config
        # Run the async initialize() method if it exists
        if hasattr(self.sdk_strategy, 'initialize'):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Initialize with parameters passed to adapter
                    loop.run_until_complete(self.sdk_strategy.initialize(self.parameters))
                    logger.info(f"SDK strategy {self.name} initialized successfully")
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
            except Exception as e:
                logger.error(f"Error initializing SDK strategy {self.name}: {e}", exc_info=True)

    def on_unload(self) -> None:
        """Hook called when strategy is unloaded."""
        # SDK strategies can implement their own cleanup
        pass


def load_sdk_strategy(module: str, class_name: str, name: str, **parameters) -> SDKStrategyAdapter:
    """Load a strategy from SDK and wrap it in an adapter.

    Args:
        module: Python module path (e.g., "strategies.official.rapid_rise")
        class_name: Strategy class name (e.g., "RapidRiseStrategy")
        name: Instance name for this strategy
        **parameters: Configuration parameters for the strategy

    Returns:
        SDKStrategyAdapter wrapping the loaded SDK strategy
    """
    import importlib

    # Import the module containing the strategy
    mod = importlib.import_module(module)
    strategy_class = getattr(mod, class_name)

    # Instantiate the SDK strategy
    sdk_strategy = strategy_class(**parameters)

    # Wrap in adapter
    return SDKStrategyAdapter(sdk_strategy=sdk_strategy, name=name, **parameters)