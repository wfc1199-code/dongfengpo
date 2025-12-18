"""
AI Quant Platform - DataManager
Unified data layer with Tushare as primary source and DuckDB caching.

Features:
- Single entry point for all data access
- DuckDB local caching
- Tushare rate limiting integration
- Real-time and historical data support
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

import pandas as pd

from .tushare_client import TushareClient
from .duckdb_manager import DuckDBManager
from .rate_limiter import get_rate_limiter, RateLimitConfig

logger = logging.getLogger(__name__)


@dataclass
class DataManagerConfig:
    """Configuration for DataManager."""
    tushare_token: Optional[str] = None
    duckdb_path: str = "./quant_data/quant.duckdb"
    cache_minute_days: int = 30      # Keep 30 days of minute data
    cache_daily_days: int = 365      # Keep 1 year of daily data
    realtime_cache_ttl_seconds: float = 5.0  # Cache realtime data for 5 seconds
    validation_threshold: float = 0.95  # Require 95% completeness


class DataManager:
    """
    Unified data manager for AI Quant Platform.
    
    Responsibilities:
    - Provide single entry point for all data access
    - Manage DuckDB local cache
    - Handle Tushare API calls with rate limiting
    - Support both realtime and historical data
    
    Usage:
        dm = DataManager()
        
        # Historical data (from cache or Tushare)
        daily = dm.get_daily("000001.SZ", days=30)
        minute = dm.get_minute("000001.SZ", days=5)
        
        # Real-time data
        realtime = await dm.get_realtime(["000001", "600000"])
        
        # Sync data
        await dm.sync_today()
    """
    
    def __init__(self, config: Optional[DataManagerConfig] = None):
        self.config = config or DataManagerConfig()
        
        # Initialize components
        self.tushare = TushareClient(token=self.config.tushare_token)
        self.duckdb = DuckDBManager(self.config.duckdb_path)
        self.rate_limiter = get_rate_limiter(RateLimitConfig())
        
        # Realtime cache with lock for thread-safety
        self._realtime_cache: Dict[str, Dict[str, Any]] = {}  # symbol -> {data, timestamp}
        self._cache_lock = asyncio.Lock()
        
        logger.info("DataManager initialized")
    
    # ==================== Historical Data ====================
    
    def get_daily(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        Get daily K-line data.
        
        Priority:
        1. Local parquet file (fastest, from daily_data/)
        2. DuckDB cache
        3. Tushare API (slowest, rate limited)
        
        Args:
            symbol: Stock symbol (6 digits, e.g., '000001')
            days: Number of days to fetch
        
        Returns:
            DataFrame with OHLCV data
        """
        ts_code = self._to_ts_code(symbol)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        
        # 1️⃣ Try local daily parquet file FIRST
        parquet_file = Path(self.config.duckdb_path) / "daily_data" / f"{ts_code}.parquet"
        if parquet_file.exists():
            try:
                import pyarrow.parquet as pq
                table = pq.read_table(parquet_file)
                df = table.to_pandas()
                
                # Filter by date range
                if 'trade_date' in df.columns:
                    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
                    mask = (df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)
                    df = df[mask]
                    
                    if len(df) > 0:
                        logger.debug(f"✅ Daily parquet hit for {symbol}: {len(df)} rows from {parquet_file.name}")
                        return df
            except Exception as e:
                logger.warning(f"Failed to read daily parquet {parquet_file.name}: {e}")
        
        # 2️⃣ Try DuckDB cache
        cached = self.duckdb.query_daily(ts_code, start_date, end_date)
        if cached is not None and len(cached) > 0:
            logger.debug(f"DuckDB daily cache hit for {symbol}: {len(cached)} rows")
            return cached
        
        # 3️⃣ Last resort - fetch from Tushare
        logger.info(f"Daily cache miss for {symbol}, fetching from Tushare API")
        df = self._fetch_daily_from_tushare(ts_code, start_date, end_date)
        
        if not df.empty:
            self.duckdb.upsert_daily(df)
        
        return df
    
    def get_minute(self, symbol: str, days: int = 5, freq: str = "1min") -> pd.DataFrame:
        """
        Get minute-level K-line data.
        
        Priority:
        1. Local parquet file (fastest, from persist_minute_data.py)
        2. DuckDB checkpoint cache
        3. Tushare API (slowest, rate limited)
        
        Args:
            symbol: Stock symbol (6 digits)
            days: Number of days to fetch
            freq: Frequency ('1min', '5min', '15min', '30min', '60min')
        
        Returns:
            DataFrame with minute OHLCV data
        """
        ts_code = self._to_ts_code(symbol)
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        # 1️⃣ Try local parquet file FIRST (persisted data)
        parquet_file = Path(self.config.duckdb_path).parent / "market_data" / f"{ts_code}.parquet"
        if parquet_file.exists():
            try:
                import pyarrow.parquet as pq
                table = pq.read_table(parquet_file)
                df = table.to_pandas()
                
                # Filter by date range
                if 'datetime' in df.columns:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    mask = (df['datetime'] >= start_time) & (df['datetime'] <= end_time)
                    df = df[mask]
                    
                    if len(df) > 0:
                        logger.debug(f"✅ Parquet file hit for {symbol}: {len(df)} rows from {parquet_file.name}")
                        return df
            except Exception as e:
                logger.warning(f"Failed to read parquet file {parquet_file.name}: {e}")
        
        # 2️⃣ Try DuckDB checkpoint cache
        cached = self.duckdb.query_minute(ts_code, start_time, end_time)
        if cached is not None and len(cached) > 0:
            logger.debug(f"DuckDB cache hit for {symbol}: {len(cached)} rows")
            return cached
        
        # 3️⃣ Last resort - fetch from Tushare
        logger.info(f"Cache miss for {symbol}, fetching from Tushare API")
        df = self._fetch_minute_from_tushare(ts_code, start_time, end_time, freq)
        
        if not df.empty:
            self.duckdb.upsert_minute(df)
        
        return df
    
    # ==================== Real-time Data ====================
    
    async def get_realtime(self, symbols: List[str]) -> pd.DataFrame:
        """
        Get real-time quotes (async with rate limiting).
        
        Uses Tushare realtime API with internal caching to reduce API calls.
        
        Args:
            symbols: List of stock symbols (6 digits)
        
        Returns:
            DataFrame with current quotes
        """
        now = time.time()
        results = []
        to_fetch = []
        
        # Check cache with lock
        async with self._cache_lock:
            for symbol in symbols:
                cached = self._realtime_cache.get(symbol)
                if cached and (now - cached["timestamp"]) < self.config.realtime_cache_ttl_seconds:
                    results.append(cached["data"])
                else:
                    to_fetch.append(symbol)
        
        # Fetch uncached symbols
        if to_fetch:
            # Rate limit
            await self.rate_limiter.acquire()
            
            # Fetch from Tushare (async)
            ts_codes = [self._to_ts_code(s) for s in to_fetch]
            df = await self._fetch_realtime_async(ts_codes)
            
            # Update cache with lock
            async with self._cache_lock:
                for _, row in df.iterrows():
                    symbol = self._from_ts_code(row.get("ts_code", ""))
                    self._realtime_cache[symbol] = {
                        "data": row.to_dict(),
                        "timestamp": now
                    }
                    results.append(row.to_dict())
        
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    # ==================== Data Sync ====================
    
    async def sync_today(self) -> Dict[str, Any]:
        """
        Sync today's data for all tracked symbols.
        
        Returns:
            Sync status with counts and validation results
        """
        logger.info("Starting daily data sync")
        
        # Get stock list
        stocks = self.tushare.get_stock_list()
        symbols = stocks["ts_code"].tolist()[:50]  # Limit for safety
        
        synced = 0
        failed = 0
        
        for ts_code in symbols:
            try:
                await self._sync_symbol_today(ts_code)
                synced += 1
            except Exception as e:
                logger.error(f"Failed to sync {ts_code}: {e}")
                failed += 1
            
            # Rate limit between symbols
            await asyncio.sleep(0.2)
        
        logger.info(f"Sync completed: {synced} success, {failed} failed")
        
        return {
            "synced": synced,
            "failed": failed,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _sync_symbol_today(self, ts_code: str):
        """Sync today's minute and daily data for a symbol."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Rate limit
        await self.rate_limiter.acquire()
        
        # Fetch minute data
        minute_df = self.tushare.get_minute_data(
            ts_code,
            f"{today} 09:30:00",
            f"{today} 15:00:00",
            freq="1min"
        )
        
        if not minute_df.empty:
            minute_df["ts_code"] = ts_code
            self.duckdb.upsert_minute(minute_df)
    
    # ==================== Data Validation ====================
    
    def validate_minute_data(self, symbol: str, date: str) -> bool:
        """
        Validate minute data completeness.
        
        Args:
            symbol: Stock symbol
            date: Date to validate (YYYY-MM-DD)
        
        Returns:
            True if data is complete (>= 95% of expected 240 bars)
        """
        ts_code = self._to_ts_code(symbol)
        start_time = f"{date} 09:30:00"
        end_time = f"{date} 15:00:00"
        
        df = self.duckdb.query_minute(ts_code, start_time, end_time)
        if df is None:
            return False
        
        count = len(df)
        expected = 240  # 4 hours * 60 minutes
        completeness = count / expected
        
        if completeness < self.config.validation_threshold:
            logger.warning(f"{symbol} {date}: {count}/240 bars ({completeness:.1%})")
            return False
        
        return True
    
    async def validate_today(self) -> Dict[str, Any]:
        """Validate today's data for all synced symbols."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get synced symbols from DuckDB
        symbols = self.duckdb.get_synced_symbols(today)
        
        passed = 0
        failed = []
        
        for symbol in symbols:
            if self.validate_minute_data(symbol, today):
                passed += 1
            else:
                failed.append(symbol)
        
        return {
            "date": today,
            "passed": passed,
            "failed": len(failed),
            "failed_symbols": failed[:10]  # Top 10
        }
    
    # ==================== Helpers ====================
    
    def _to_ts_code(self, symbol: str) -> str:
        """Convert 6-digit symbol to Tushare ts_code format."""
        if "." in symbol:
            return symbol
        if symbol.startswith("6"):
            return f"{symbol}.SH"
        else:
            return f"{symbol}.SZ"
    
    def _from_ts_code(self, ts_code: str) -> str:
        """Convert ts_code to 6-digit symbol."""
        return ts_code.split(".")[0] if "." in ts_code else ts_code
    
    async def _fetch_daily_async(self, ts_code: str, start: str, end: str) -> pd.DataFrame:
        """Fetch daily data from Tushare with rate limiting."""
        await self.rate_limiter.acquire()
        try:
            df = self.tushare.pro.daily(ts_code=ts_code, start_date=start, end_date=end)
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to fetch daily {ts_code}: {type(e).__name__}")
            return pd.DataFrame()
    
    def _fetch_daily_from_tushare(self, ts_code: str, start: str, end: str) -> pd.DataFrame:
        """Fetch daily data from Tushare (sync, uses rate limiter interval)."""
        # Use min interval from rate limiter config
        time.sleep(self.rate_limiter.config.min_interval_ms / 1000.0)
        try:
            df = self.tushare.pro.daily(ts_code=ts_code, start_date=start, end_date=end)
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to fetch daily {ts_code}: {type(e).__name__}")
            return pd.DataFrame()
    
    def _fetch_minute_from_tushare(self, ts_code: str, start: str, end: str, freq: str) -> pd.DataFrame:
        """
        Fetch minute data from Tushare, with AkShare fallback.
        
        Note: Tushare stk_mins requires separate permission beyond points.
        Falls back to AkShare if Tushare fails.
        """
        try:
            df = self.tushare.get_minute_data(ts_code, start, end, freq)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"Tushare minute data failed for {ts_code}: {e}")
        
        # Fallback to AkShare
        logger.info(f"Falling back to AkShare for minute data: {ts_code}")
        return self._fetch_minute_from_akshare(ts_code, freq)
    
    def _fetch_minute_from_akshare(self, ts_code: str, freq: str = "1") -> pd.DataFrame:
        """
        Fetch minute data from AkShare (免费, 无积分限制).
        
        Uses: stock_zh_a_minute (新版API，更快更稳定)
        """
        try:
            import akshare as ak
            
            # Convert ts_code to AkShare format (000001.SZ -> 000001)
            symbol = ts_code.split('.')[0]
            
            # Map freq: '1min' -> '1', '5min' -> '5'
            period = freq.replace('min', '') if 'min' in freq else freq
            
            # 尝试新版API: stock_zh_a_minute
            try:
                df = ak.stock_zh_a_minute(
                    symbol=symbol,
                    period=period,
                    adjust=""
                )
            except (AttributeError, TypeError):
                # 降级到旧版API
                logger.debug(f"stock_zh_a_minute not available, using stock_zh_a_hist_min_em")
                df = ak.stock_zh_a_hist_min_em(
                    symbol=symbol,
                    period=period,
                    adjust=""
                )
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # Normalize columns
            df = df.rename(columns={
                '时间': 'datetime',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
            })
            
            # Ensure required columns
            required = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            for col in required:
                if col not in df.columns:
                    df[col] = 0
            
            if 'amount' not in df.columns:
                df['amount'] = df['close'] * df['volume']
            
            logger.info(f"AkShare minute data for {symbol}: {len(df)} bars")
            return df[['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount']]
            
        except Exception as e:
            logger.error(f"AkShare minute data failed for {ts_code}: {e}")
            return pd.DataFrame()
    
    async def _fetch_realtime_async(self, ts_codes: List[str]) -> pd.DataFrame:
        """Fetch realtime quotes from Tushare (async)."""
        try:
            # Run sync API call in executor to not block event loop
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: self.tushare.pro.quotes(ts_code=",".join(ts_codes))
            )
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to fetch realtime: {type(e).__name__}")
            return pd.DataFrame()
    
    def _fetch_realtime_from_tushare(self, ts_codes: List[str]) -> pd.DataFrame:
        """Fetch realtime quotes from Tushare (sync)."""
        try:
            df = self.tushare.pro.quotes(ts_code=",".join(ts_codes))
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to fetch realtime: {type(e).__name__}")
            return pd.DataFrame()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get DataManager statistics."""
        return {
            "rate_limiter": self.rate_limiter.get_stats(),
            "cache_size": len(self._realtime_cache),
            "duckdb_path": self.config.duckdb_path,
        }
