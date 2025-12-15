"""Tencent quote adapter implementation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Dict, Iterable, List, Optional

import aiohttp

from .base import AdapterTick, DataSourceAdapter

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TencentAdapterConfig:
    """Configuration options for the Tencent adapter."""

    base_url: str = "http://qt.gtimg.cn/q="
    poll_interval: float = 1.0
    request_timeout: float = 5.0
    max_symbols_per_request: int = 200


class TencentAdapter(DataSourceAdapter):
    """Fetch realtime quotes from Tencent quote API."""

    def __init__(self, *, config: Optional[TencentAdapterConfig] = None) -> None:
        super().__init__(name="tencent")
        self.config = config or TencentAdapterConfig()
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:  # noqa: D401 - documentation inherited
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self) -> None:  # noqa: D401 - documentation inherited
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def stream(self, symbols: Iterable[str]) -> AsyncIterator[AdapterTick]:
        """Continuously fetch and yield tick records."""

        normalized = self._normalize_symbols(symbols)
        if not normalized:
            logger.warning("TencentAdapter received empty symbol list")
            return

        while True:
            try:
                for batch in self._chunk_symbols(normalized, self.config.max_symbols_per_request):
                    ticks = await self._fetch_batch(batch)
                    for tick in ticks:
                        yield tick
                await asyncio.sleep(self.config.poll_interval)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tencent adapter polling failed: %s", exc)
                await asyncio.sleep(self.config.poll_interval)

    async def fetch_snapshot(self, symbol: str) -> AdapterTick:
        symbols = self._normalize_symbols([symbol])
        if not symbols:
            raise ValueError("Invalid symbol provided")
        ticks = await self._fetch_batch(symbols)
        if not ticks:
            raise RuntimeError(f"No tick data returned for symbol {symbol}")
        return ticks[0]

    def _normalize_symbols(self, symbols: Iterable[str]) -> List[str]:
        normalized = []
        for symbol in symbols:
            if not symbol:
                continue
            symbol = symbol.strip()
            if not symbol:
                continue
            if symbol.startswith("sh") or symbol.startswith("sz"):
                normalized.append(symbol)
            else:
                if symbol.startswith("6"):
                    normalized.append(f"sh{symbol}")
                elif symbol[0].isdigit():
                    normalized.append(f"sz{symbol}")
                else:
                    logger.debug("Skipping unsupported symbol: %s", symbol)
        return normalized

    def _chunk_symbols(self, symbols: List[str], size: int) -> List[List[str]]:
        return [symbols[i : i + size] for i in range(0, len(symbols), size)]

    async def _fetch_batch(self, symbols: List[str]) -> List[AdapterTick]:
        if not symbols:
            return []

        if not self._session:
            raise RuntimeError("TencentAdapter has not been started")

        url = f"{self.config.base_url}{','.join(symbols)}"
        async with self._session.get(url) as response:
            text = await response.text(encoding="gbk", errors="ignore")
        return self._parse_response(text)

    def _parse_response(self, payload: str) -> List[AdapterTick]:
        ticks: List[AdapterTick] = []
        for line in payload.strip().split("\n"):
            if not line or "=" not in line:
                continue
            symbol, data = self._parse_line(line)
            if symbol and data:
                ticks.append(self._build_tick(symbol, data, line))
        return ticks

    def _parse_line(self, line: str) -> tuple[Optional[str], Optional[List[str]]]:
        try:
            head, tail = line.split("=", 1)
            symbol = head.split("_", 1)[1]
            values = tail.strip('";').split("~")
            return symbol, values
        except (IndexError, ValueError):
            logger.debug("Failed to parse Tencent line: %s", line)
            return None, None

    def _build_tick(self, symbol: str, values: List[str], raw_line: str) -> AdapterTick:
        def _safe_float(index: int) -> float:
            try:
                return float(values[index]) if values[index] else 0.0
            except (IndexError, ValueError):
                return 0.0

        def _safe_int(index: int) -> int:
            try:
                if not values[index]:
                    return 0
                return int(float(values[index]))
            except (IndexError, ValueError):
                return 0

        price = _safe_float(3)
        volume = _safe_int(6)
        turnover = _safe_float(7)

        # Tencent payload exposes bid/ask data in later fields, but those fields
        # are not required for the collector at this stage. Leave them unset to
        # keep the adapter resilient to format variations.
        bid_price: Optional[float] = None
        bid_volume: Optional[int] = None
        ask_price: Optional[float] = None
        ask_volume: Optional[int] = None
        timestamp = datetime.utcnow()

        raw: Dict[str, object] = {"line": raw_line, "fields": values}

        return AdapterTick(
            symbol=symbol,
            price=price,
            volume=volume,
            turnover=turnover,
            bid_price=bid_price,
            bid_volume=bid_volume,
            ask_price=ask_price,
            ask_volume=ask_volume,
            timestamp=timestamp,
            raw=raw,
        )
