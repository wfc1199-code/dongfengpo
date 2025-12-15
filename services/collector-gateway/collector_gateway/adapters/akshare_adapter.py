"""AkShare data source adapter."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import AsyncIterator, Iterable

try:
    import akshare as ak
except ImportError:
    ak = None

from .base import AdapterTick, DataSourceAdapter

logger = logging.getLogger(__name__)


class AkShareAdapter(DataSourceAdapter):
    """
    Adapter for AkShare real-time data source.

    Uses AkShare library to fetch real-time stock quotes.
    """

    def __init__(self, name: str = "akshare", poll_interval: float = 1.0):
        super().__init__(name)
        self.poll_interval = poll_interval
        self._running = False

        if ak is None:
            raise ImportError("akshare package is required for AkShareAdapter")

    async def start(self) -> None:
        """Initialize the adapter."""
        self._running = True
        logger.info("AkShareAdapter started")

    async def stop(self) -> None:
        """Stop the adapter."""
        self._running = False
        logger.info("AkShareAdapter stopped")

    async def stream(self, symbols: Iterable[str]) -> AsyncIterator[AdapterTick]:
        """
        Stream real-time ticks for given symbols.

        Polls AkShare at regular intervals.
        """
        symbols_list = list(symbols)

        while self._running:
            try:
                # Fetch batch of quotes
                for symbol in symbols_list:
                    try:
                        tick = await self.fetch_snapshot(symbol)
                        yield tick
                    except Exception as e:
                        logger.warning(f"Failed to fetch {symbol} from AkShare: {e}")
                        continue

                # Wait before next poll
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"AkShare stream error: {e}")
                await asyncio.sleep(self.poll_interval * 2)

    async def fetch_snapshot(self, symbol: str) -> AdapterTick:
        """
        Fetch a single tick snapshot from AkShare.

        Args:
            symbol: Stock code (e.g., "sh600000", "sz000001")
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        raw_data = await loop.run_in_executor(None, self._fetch_quote, symbol)

        # Parse AkShare response
        return self._parse_quote(symbol, raw_data)

    def _fetch_quote(self, symbol: str) -> dict:
        """Fetch quote from AkShare (blocking)."""
        try:
            # Convert symbol format: sh600000 -> 600000
            # sz000001 -> 000001
            clean_symbol = symbol[2:] if len(symbol) > 6 else symbol

            # Use stock_zh_a_spot_em for real-time quotes
            df = ak.stock_zh_a_spot_em()

            # Filter for our symbol
            result = df[df['代码'] == clean_symbol]

            if result.empty:
                raise ValueError(f"Symbol {symbol} not found in AkShare data")

            return result.iloc[0].to_dict()

        except Exception as e:
            logger.error(f"AkShare API error for {symbol}: {e}")
            raise

    def _parse_quote(self, symbol: str, raw: dict) -> AdapterTick:
        """Parse AkShare quote data to AdapterTick."""
        try:
            return AdapterTick(
                symbol=symbol,
                price=float(raw.get('最新价', 0)),
                volume=int(raw.get('成交量', 0)),
                turnover=float(raw.get('成交额', 0)),
                bid_price=float(raw.get('买一价', 0)) if raw.get('买一价') else None,
                bid_volume=int(raw.get('买一量', 0)) if raw.get('买一量') else None,
                ask_price=float(raw.get('卖一价', 0)) if raw.get('卖一价') else None,
                ask_volume=int(raw.get('卖一量', 0)) if raw.get('卖一量') else None,
                timestamp=datetime.now(),
                raw=raw
            )
        except Exception as e:
            logger.error(f"Failed to parse AkShare data for {symbol}: {e}")
            raise
