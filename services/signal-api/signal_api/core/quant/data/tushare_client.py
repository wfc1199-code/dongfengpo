"""
AI Quant Platform - Tushare Client
Enterprise-grade wrapper for Tushare Pro API with retry and resume support.

Features:
- Exponential backoff retry on failures
- Checkpoint-based resume for interrupted downloads
- Rate limiting to respect API quotas
- Secure token handling
"""

import os
import json
import time
import logging
from time import perf_counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)

# Column mapping for data normalization
COLUMN_MAPPING = {
    "trade_time": "datetime",
    "vol": "volume"
}


class TushareClient:
    """
    Production-grade Tushare Pro API client.
    
    Features:
    1. Retry with exponential backoff
    2. Checkpoint-based resume
    3. Rate limiting (respects API quotas)
    4. Data normalization
    5. Secure token handling (no logging)
    """
    
    # API rate limits (conservative for safety)
    CALLS_PER_MINUTE = 150
    CALL_DELAY_MS = 400  # ~150 calls/minute
    
    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF_SECONDS = 1
    
    def __init__(self, token: Optional[str] = None, checkpoint_dir: str = "./quant_data"):
        """
        Initialize the Tushare client.
        
        Args:
            token: Tushare Pro API token. If None, reads from TUSHARE_TOKEN env var.
            checkpoint_dir: Directory for storing download checkpoints.
        """
        self._token = token or os.environ.get("TUSHARE_TOKEN")
        if not self._token:
            raise ValueError("Tushare token required. Set TUSHARE_TOKEN env var or pass token.")
        
        self.checkpoint_path = Path(checkpoint_dir) / "tushare_checkpoint.json"
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._pro = None
        self._last_call_time: float = 0.0
        
        # Log initialization without exposing token
        logger.info("TushareClient initialized (token set)")
    
    def __repr__(self) -> str:
        """Safe representation without token."""
        return f"TushareClient(checkpoint_dir='{self.checkpoint_path.parent}')"
    
    @property
    def token(self) -> str:
        """Token property - avoid direct access in logs."""
        return self._token
    
    @property
    def pro(self):
        """Lazy initialization of Tushare Pro API."""
        if self._pro is None:
            import tushare as ts
            ts.set_token(self._token)
            self._pro = ts.pro_api()
            logger.info("Tushare Pro API connected")
        return self._pro
    
    def _rate_limit(self):
        """Enforce API rate limiting with high precision."""
        elapsed_ms = (perf_counter() - self._last_call_time) * 1000
        if elapsed_ms < self.CALL_DELAY_MS:
            sleep_time = (self.CALL_DELAY_MS - elapsed_ms) / 1000
            time.sleep(sleep_time)
        self._last_call_time = perf_counter()
    
    def _call_api(self, method: str, **kwargs) -> pd.DataFrame:
        """
        Call Tushare API with retry logic.
        
        Args:
            method: API method name (e.g., 'stk_mins', 'moneyflow')
            **kwargs: API parameters
        
        Returns:
            DataFrame from API response.
        """
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                self._rate_limit()
                api_func = getattr(self.pro, method)
                df = api_func(**kwargs)
                return df if df is not None else pd.DataFrame()
                
            except Exception as e:
                last_exception = e
                backoff = self.INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(f"API call failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                
                if attempt < self.MAX_RETRIES - 1:
                    logger.info(f"Retrying in {backoff}s...")
                    time.sleep(backoff)
        
        # All retries failed
        logger.error(f"API call failed after {self.MAX_RETRIES} attempts: {method}")
        if last_exception:
            raise last_exception
        return pd.DataFrame()
    
    def get_minute_data(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        freq: str = "1min"
    ) -> pd.DataFrame:
        """
        Get minute-level data for a stock.
        
        优先使用 rt_min (实时分钟) 接口，失败后尝试 stk_mins (历史分钟)。
        
        Args:
            ts_code: Stock code (e.g., '000001.SZ')
            start_date: Start date 'YYYY-MM-DD HH:MM:SS'
            end_date: End date 'YYYY-MM-DD HH:MM:SS'
            freq: Frequency ('1min', '5min', '15min', '30min', '60min')
        
        Returns:
            DataFrame with columns: datetime, open, high, low, close, volume, amount
        """
        logger.info(f"Fetching {freq} data for {ts_code}: {start_date} to {end_date}")
        
        # 转换 freq 格式: '1min' -> '1MIN' for rt_min
        rt_freq = freq.upper().replace('MIN', 'MIN')  # '1min' -> '1MIN'
        if not rt_freq.endswith('MIN'):
            rt_freq = rt_freq + 'MIN'
        
        df = pd.DataFrame()
        
        # 方法1: 尝试 rt_min (实时分钟，用户有权限)
        try:
            df = self._call_api(
                "rt_min",
                ts_code=ts_code,
                freq=rt_freq
            )
            if df is not None and not df.empty:
                logger.info(f"rt_min success for {ts_code}: {len(df)} bars")
        except Exception as e:
            logger.debug(f"rt_min failed for {ts_code}: {e}")
        
        # 方法2: 如果 rt_min 失败，尝试 stk_mins (历史分钟)
        if df is None or df.empty:
            try:
                df = self._call_api(
                    "stk_mins",
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                    freq=freq
                )
            except Exception as e:
                logger.warning(f"stk_mins also failed for {ts_code}: {e}")
                return pd.DataFrame()
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Normalize column names
        # rt_min uses: time, open, close, high, low, vol, amount
        rename_map = {
            'time': 'datetime',
            'trade_time': 'datetime',
            'vol': 'volume',
        }
        rename_cols = {k: v for k, v in rename_map.items() if k in df.columns}
        if rename_cols:
            df = df.rename(columns=rename_cols)
        
        # Ensure proper types
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
        
        logger.info(f"Retrieved {len(df)} bars for {ts_code}")
        return df
    
    def get_money_flow(self, trade_date: str) -> pd.DataFrame:
        """
        Get individual stock money flow data for a trading day.
        
        Args:
            trade_date: Trading date 'YYYYMMDD'
        
        Returns:
            DataFrame with money flow indicators.
        """
        logger.info(f"Fetching money flow for {trade_date}")
        
        df = self._call_api("moneyflow", trade_date=trade_date)
        
        if not df.empty:
            logger.info(f"Retrieved money flow for {len(df)} stocks")
        
        return df
    
    def get_stock_list(self) -> pd.DataFrame:
        """Get list of all A-share stocks."""
        logger.info("Fetching stock list")
        df = self._call_api("stock_basic", exchange="", list_status="L")
        logger.info(f"Retrieved {len(df)} stocks")
        return df
    
    # --- Checkpoint Management ---
    
    def save_checkpoint(self, checkpoint_data: Dict[str, Any]):
        """
        Save download progress checkpoint with atomic write.
        
        Args:
            checkpoint_data: Dictionary with checkpoint state.
        """
        # Remove any sensitive data before saving
        safe_data = {k: v for k, v in checkpoint_data.items() if k != 'token'}
        
        try:
            # Ensure directory exists
            self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Atomic write: write to temp file first, then rename
            temp_path = self.checkpoint_path.with_suffix('.json.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(safe_data, f, indent=2, default=str, ensure_ascii=False)
            temp_path.rename(self.checkpoint_path)
            
            logger.debug(f"Checkpoint saved: {list(safe_data.keys())}")
            
        except PermissionError as e:
            logger.error(f"Permission denied writing checkpoint: {e}")
            raise
        except OSError as e:
            logger.error(f"Failed to write checkpoint (disk full?): {e}")
            raise
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load previous checkpoint if exists."""
        if not self.checkpoint_path.exists():
            return None
        
        try:
            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Checkpoint loaded: {list(data.keys())}")
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted checkpoint file: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return None
    
    def clear_checkpoint(self):
        """Clear checkpoint after successful completion."""
        if self.checkpoint_path.exists():
            try:
                self.checkpoint_path.unlink()
                logger.info("Checkpoint cleared")
            except OSError as e:
                logger.warning(f"Failed to clear checkpoint: {e}")
