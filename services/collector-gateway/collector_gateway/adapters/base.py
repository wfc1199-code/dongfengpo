"""Base definitions for data source adapters."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Dict, Iterable, Optional


@dataclass(slots=True)
class AdapterTick:
    """Normalized tick data emitted by adapters."""

    symbol: str
    price: float
    volume: int
    turnover: float
    bid_price: Optional[float]
    bid_volume: Optional[int]
    ask_price: Optional[float]
    ask_volume: Optional[int]
    timestamp: datetime
    raw: Dict[str, object]


class DataSourceAdapter(abc.ABC):
    """Abstract base class for data source adapters."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    async def start(self) -> None:
        """Hook invoked before the adapter starts streaming."""

    async def stop(self) -> None:
        """Hook invoked when the adapter is stopped."""

    @abc.abstractmethod
    async def stream(self, symbols: Iterable[str]) -> AsyncIterator[AdapterTick]:
        """Yield tick records for the requested symbols."""

    @abc.abstractmethod
    async def fetch_snapshot(self, symbol: str) -> AdapterTick:
        """Fetch a single tick snapshot for the given symbol."""
