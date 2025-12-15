"""Tushare data source adapter."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import AsyncIterator, Iterable, Optional

try:
    import tushare as ts
except ImportError:
    ts = None

from .base import AdapterTick, DataSourceAdapter

logger = logging.getLogger(__name__)


class TushareAdapter(DataSourceAdapter):
    """
    Adapter for Tushare data source.

    Requires TUSHARE_TOKEN environment variable or explicit token.
    """

    def __init__(
        self,
        name: str = "tushare",
        token: Optional[str] = None,
        poll_interval: float = 1.0
    ):
        super().__init__(name)
        self.poll_interval = poll_interval
        self._running = False
        self.pro = None

        if ts is None:
            raise ImportError("tushare package is required for TushareAdapter")

        # Get token from parameter or environment
        self.token = token or os.environ.get('TUSHARE_TOKEN')
        if not self.token:
            raise ValueError("TUSHARE_TOKEN is required for TushareAdapter")

    async def start(self) -> None:
        """Initialize Tushare Pro API."""
        try:
            ts.set_token(self.token)
            self.pro = ts.pro_api()
            self._running = True
            logger.info("TushareAdapter started")
        except Exception as e:
            logger.error(f"Failed to initialize Tushare: {e}")
            raise

    async def stop(self) -> None:
        """Stop the adapter."""
        self._running = False
        self.pro = None
        logger.info("TushareAdapter stopped")

    async def stream(self, symbols: Iterable[str]) -> AsyncIterator[AdapterTick]:
        """
        Stream real-time ticks for given symbols.

        Polls Tushare at regular intervals.
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
                        logger.warning(f"Failed to fetch {symbol} from Tushare: {e}")
                        continue

                # Wait before next poll (Tushare has rate limits)
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Tushare stream error: {e}")
                await asyncio.sleep(self.poll_interval * 2)

    async def fetch_snapshot(self, symbol: str) -> AdapterTick:
        """
        Fetch a single tick snapshot from Tushare.

        Args:
            symbol: Stock code in Tushare format (e.g., "600000.SH", "000001.SZ")
        """
        if not self.pro:
            raise RuntimeError("Tushare Pro API not initialized")

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        raw_data = await loop.run_in_executor(None, self._fetch_quote, symbol)

        # Parse Tushare response
        return self._parse_quote(symbol, raw_data)

    def _fetch_quote(self, symbol: str) -> dict:
        """Fetch quote from Tushare (blocking)."""
        try:
            # Convert symbol format: sh600000 -> 600000.SH, sz000001 -> 000001.SZ
            ts_symbol = self._convert_symbol_format(symbol)

            # Use realtime quote API
            df = self.pro.daily(ts_code=ts_symbol, start_date='', end_date='')

            if df.empty:
                # Fallback to query from index
                df = self.pro.query('daily', ts_code=ts_symbol)

            if df.empty:
                raise ValueError(f"Symbol {symbol} not found in Tushare data")

            # Get most recent quote
            return df.iloc[0].to_dict()

        except Exception as e:
            logger.error(f"Tushare API error for {symbol}: {e}")
            raise

    def _convert_symbol_format(self, symbol: str) -> str:
        """Convert symbol from internal format to Tushare format."""
        # sh600000 -> 600000.SH
        # sz000001 -> 000001.SZ
        if symbol.startswith('sh'):
            return f"{symbol[2:]}.SH"
        elif symbol.startswith('sz'):
            return f"{symbol[2:]}.SZ"
        elif '.' in symbol:
            return symbol  # Already in Tushare format
        else:
            # Assume SH if no prefix
            return f"{symbol}.SH"

    def _parse_quote(self, symbol: str, raw: dict) -> AdapterTick:
        """Parse Tushare quote data to AdapterTick."""
        try:
            return AdapterTick(
                symbol=symbol,
                price=float(raw.get('close', 0)),
                volume=int(raw.get('vol', 0) * 100),  # Tushare vol is in 100 shares
                turnover=float(raw.get('amount', 0) * 1000),  # Tushare amount is in 1000 yuan
                bid_price=None,  # Not available in daily data
                bid_volume=None,
                ask_price=None,
                ask_volume=None,
                timestamp=datetime.now(),
                raw=raw
            )
        except Exception as e:
            logger.error(f"Failed to parse Tushare data for {symbol}: {e}")
            raise
