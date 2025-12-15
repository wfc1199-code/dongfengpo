"""
东风破策略插件SDK
"""

from .base_strategy import BaseStrategy, Signal, SignalType
from .decorators import strategy, on_market_open, on_market_close
from .registry import StrategyRegistry

__version__ = "1.0.0"
__all__ = [
    "BaseStrategy",
    "Signal",
    "SignalType",
    "strategy",
    "on_market_open",
    "on_market_close",
    "StrategyRegistry"
]