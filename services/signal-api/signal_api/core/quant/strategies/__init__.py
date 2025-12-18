# AI Quant Platform - Trading Strategies
from .base import BaseStrategy, StrategyConfig, Signal, SignalType
from .ambush import AmbushStrategy, AmbushConfig
from .ignition import IgnitionStrategy, IgnitionConfig

__all__ = [
    "BaseStrategy", "StrategyConfig", "Signal", "SignalType",
    "AmbushStrategy", "AmbushConfig",
    "IgnitionStrategy", "IgnitionConfig",
]
