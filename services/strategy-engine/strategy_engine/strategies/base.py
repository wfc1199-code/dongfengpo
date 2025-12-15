"""Base definitions for strategy plugins."""

from __future__ import annotations

import abc
from typing import Optional

from ..models import FeatureSnapshot, StrategySignal


class Strategy(abc.ABC):
    """Abstract base class for strategy plugins."""

    def __init__(self, name: str, **parameters) -> None:
        self.name = name
        self.parameters = parameters

    @abc.abstractmethod
    def evaluate(self, feature: FeatureSnapshot) -> Optional[StrategySignal]:
        """Return strategy signal for the given feature snapshot if triggered."""

    def on_load(self) -> None:
        """Hook called when the strategy is instantiated."""

    def on_unload(self) -> None:
        """Hook called when the strategy is unloaded."""
