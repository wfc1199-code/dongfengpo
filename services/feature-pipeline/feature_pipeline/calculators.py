"""Feature calculation utilities."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, Dict, Iterable, List

from .models import CleanTick, FeatureSnapshot


@dataclass
class RollingWindow:
    name: str
    duration: timedelta
    items: Deque[CleanTick]

    def add(self, tick: CleanTick) -> None:
        self.items.append(tick)

    def trim(self, now: datetime) -> None:
        while self.items and (now - self.items[0].timestamp) > self.duration:
            self.items.popleft()

    def stats(self) -> FeatureSnapshot:
        if not self.items:
            raise ValueError("No data in rolling window")

        prices = [item.price for item in self.items]
        volumes = [item.volume for item in self.items]
        turnovers = [item.turnover for item in self.items]

        price = prices[-1]
        first_price = prices[0]
        change_percent = ((price - first_price) / first_price * 100) if first_price else None

        return FeatureSnapshot(
            symbol=self.items[-1].symbol,
            window=self.name,
            timestamp=self.items[-1].timestamp,
            price=price,
            change_percent=change_percent,
            volume_sum=sum(volumes),
            avg_price=sum(prices) / len(prices),
            max_price=max(prices),
            min_price=min(prices),
            turnover_sum=sum(turnovers),
            sample_size=len(prices),
        )


class FeatureCalculator:
    """Compute rolling statistics for each symbol."""

    def __init__(self, window_configs: Dict[str, timedelta]) -> None:
        self.window_configs = window_configs
        self.windows: Dict[str, Dict[str, RollingWindow]] = {}

    def update(self, tick: CleanTick) -> List[FeatureSnapshot]:
        symbol_windows = self.windows.setdefault(tick.symbol, {})
        snapshots: List[FeatureSnapshot] = []

        for name, duration in self.window_configs.items():
            window = symbol_windows.get(name)
            if window is None:
                window = RollingWindow(name=name, duration=duration, items=deque())
                symbol_windows[name] = window

            window.add(tick)
            window.trim(tick.timestamp)

            if window.items:
                snapshots.append(window.stats())

        return snapshots
