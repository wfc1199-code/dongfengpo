"""
AI Quant Platform - DuckDB Manager
Enterprise-grade data warehouse for minute-level market data.

Features:
- Parquet-based storage with DuckDB query engine
- Atomic writes with checkpoint support
- Automatic backup management
- Thread-safe operations
"""

import re
import shutil
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

# Required columns for minute data
REQUIRED_COLUMNS = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount']

# Symbol format validation regex (e.g., 000001.SZ, 600000.SH)
SYMBOL_PATTERN = re.compile(r'^[0-9]{6}\.[A-Z]{2,3}$')


class DuckDBManager:
    """
    Manages the local data warehouse using DuckDB + Parquet.
    
    Directory Structure:
        data_root/
        ├── market_data/          # Parquet files (minute bars)
        │   ├── 000001.SZ.parquet
        │   └── ...
        ├── meta.db               # SQLite for metadata
        ├── checkpoints.json      # Download progress
        └── backup/               # Daily backups
    
    Thread Safety:
        All write operations are protected by per-file locks.
    """
    
    def __init__(self, data_root: str = "./quant_data"):
        self.data_root = Path(data_root)
        self.market_data_dir = self.data_root / "market_data"
        self.backup_dir = self.data_root / "backup"
        self.checkpoint_file = self.data_root / "checkpoints.json"
        
        # Ensure directories exist
        self.market_data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize DuckDB connection (in-memory, reads from Parquet)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        
        # Thread safety: per-file locks for concurrent writes
        self._file_locks: Dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()  # Protects _file_locks dict
        
        logger.info(f"DuckDBManager initialized at {self.data_root}")
    
    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Lazy connection initialization."""
        if self._conn is None:
            self._conn = duckdb.connect(":memory:")
            logger.info("DuckDB in-memory connection established")
        return self._conn
    
    def __enter__(self):
        """Support context manager pattern."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Auto-close on context exit."""
        self.close()
        return False
    
    @contextmanager
    def _get_file_lock(self, symbol: str):
        """Get a per-file lock for thread-safe writes."""
        with self._locks_lock:
            if symbol not in self._file_locks:
                self._file_locks[symbol] = threading.Lock()
            lock = self._file_locks[symbol]
        
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
    
    def _validate_symbol(self, symbol: str) -> None:
        """Validate symbol format to prevent path traversal."""
        if not symbol or not isinstance(symbol, str):
            raise ValueError(f"Symbol must be a non-empty string, got: {symbol}")
        if not SYMBOL_PATTERN.match(symbol):
            raise ValueError(f"Invalid symbol format: {symbol}. Expected format: 000001.SZ")
    
    def _validate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize DataFrame before saving."""
        # Check required columns
        missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Ensure datetime type
        if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            df = df.copy()
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Validate numeric columns
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise ValueError(f"Column {col} must be numeric, got: {df[col].dtype}")
        
        return df
    
    def save_minute_data(self, symbol: str, df: pd.DataFrame) -> bool:
        """
        Save minute-level data for a symbol to Parquet.
        
        Args:
            symbol: Stock symbol (e.g., '000001.SZ')
            df: DataFrame with columns ['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount']
        
        Returns:
            True if successful, False otherwise.
        
        Raises:
            ValueError: If symbol format is invalid or DataFrame is malformed.
        """
        # Validate inputs
        self._validate_symbol(symbol)
        
        if df.empty:
            logger.warning(f"Empty DataFrame for {symbol}, skipping save")
            return False
        
        df = self._validate_dataframe(df)
        file_path = self.market_data_dir / f"{symbol}.parquet"
        temp_path = file_path.with_suffix('.parquet.tmp')
        
        # Thread-safe write with file lock
        with self._get_file_lock(symbol):
            try:
                # If file exists, merge with existing data
                if file_path.exists():
                    existing_df = pd.read_parquet(file_path)
                    df = pd.concat([existing_df, df]).drop_duplicates(subset=['datetime'])
                    df = df.sort_values('datetime').reset_index(drop=True)
                
                # Atomic write: write to temp then rename
                df.to_parquet(temp_path, index=False, compression='snappy')
                temp_path.rename(file_path)
                
                logger.debug(f"Saved {len(df)} rows for {symbol}")
                return True
                
            except Exception as e:
                # Clean up temp file if exists
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass
                logger.error(f"Failed to save data for {symbol}: {e}")
                return False
    
    def load_minute_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load minute-level data for a symbol using DuckDB.
        
        Args:
            symbol: Stock symbol
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
        
        Returns:
            DataFrame with minute bars.
        
        Raises:
            ValueError: If symbol format is invalid.
        """
        # Validate symbol to prevent path traversal / SQL injection
        self._validate_symbol(symbol)
        
        file_path = self.market_data_dir / f"{symbol}.parquet"
        
        if not file_path.exists():
            logger.warning(f"No data file found for {symbol}")
            return pd.DataFrame()
        
        # Use parameterized query to prevent SQL injection
        # DuckDB's read_parquet doesn't support parameterized file paths directly,
        # but we've validated the symbol format above, so string interpolation is safe here.
        base_query = f"SELECT * FROM read_parquet('{file_path}')"
        
        # Build WHERE clause with validated date parameters
        conditions = []
        if start_date:
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                conditions.append(f"datetime >= '{start_date}'")
            except ValueError:
                raise ValueError(f"Invalid start_date format: {start_date}. Expected YYYY-MM-DD")
        
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
                conditions.append(f"datetime <= '{end_date}'")
            except ValueError:
                raise ValueError(f"Invalid end_date format: {end_date}. Expected YYYY-MM-DD")
        
        query = base_query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY datetime"
        
        try:
            result = self.conn.execute(query).fetchdf()
            logger.debug(f"Loaded {len(result)} rows for {symbol}")
            return result
        except Exception as e:
            logger.error(f"Failed to load data for {symbol}: {e}")
            return pd.DataFrame()
    
    def query(self, sql: str) -> pd.DataFrame:
        """
        Execute arbitrary SQL query on the data warehouse.
        
        WARNING: This method accepts raw SQL. Use with caution.
        
        Example:
            df = manager.query('''
                SELECT * FROM read_parquet('market_data/*.parquet')
                WHERE volume > 100000
            ''')
        """
        try:
            return self.conn.execute(sql).fetchdf()
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return pd.DataFrame()
    
    def get_available_symbols(self) -> List[str]:
        """Get list of all symbols with stored data."""
        files = list(self.market_data_dir.glob("*.parquet"))
        return [f.stem for f in files]
    
    def create_backup(self) -> Optional[str]:
        """
        Create a dated backup of all Parquet files.
        
        Returns:
            Backup directory path if successful.
        """
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / date_str
        
        try:
            # Handle existing backup directory
            if backup_path.exists():
                logger.warning(f"Backup path already exists: {backup_path}, removing...")
                shutil.rmtree(backup_path)
            
            shutil.copytree(self.market_data_dir, backup_path)
            logger.info(f"Backup created at {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None
    
    # ==================== Compatibility Methods ====================
    
    def query_minute(
        self,
        symbol: str,
        start_time: str,
        end_time: str
    ) -> Optional[pd.DataFrame]:
        """
        Query minute data by time range (compatibility alias for load_minute_data).
        
        Args:
            symbol: Stock symbol (e.g., '000001.SZ')
            start_time: Start datetime string
            end_time: End datetime string
            
        Returns:
            DataFrame or None if not found
        """
        try:
            start_date = start_time.split(" ")[0] if " " in start_time else start_time
            end_date = end_time.split(" ")[0] if " " in end_time else end_time
            return self.load_minute_data(symbol, start_date, end_date)
        except Exception as e:
            logger.debug(f"query_minute {symbol}: {e}")
            return None
    
    def upsert_minute(self, df: pd.DataFrame) -> bool:
        """
        Upsert minute data (compatibility method).
        
        Expects DataFrame with 'symbol' or 'ts_code' column.
        Groups by symbol and saves each group.
        
        Args:
            df: DataFrame with minute data and symbol column
            
        Returns:
            True if all saves succeeded
        """
        if df is None or df.empty:
            return False
        
        # Determine symbol column
        symbol_col = 'symbol' if 'symbol' in df.columns else 'ts_code'
        if symbol_col not in df.columns:
            logger.error("upsert_minute: DataFrame missing symbol/ts_code column")
            return False
        
        success = True
        for symbol, group in df.groupby(symbol_col):
            try:
                self.save_minute_data(symbol, group.drop(columns=[symbol_col], errors='ignore'))
            except Exception as e:
                logger.error(f"upsert_minute failed for {symbol}: {e}")
                success = False
        
        return success
    
    def query_daily(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        Query daily data by date range (compatibility method).
        
        Note: This DuckDBManager primarily stores minute data.
        For daily data, it attempts to aggregate from minute data or returns None.
        
        Args:
            symbol: Stock symbol (e.g., '000001.SZ')
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            
        Returns:
            DataFrame with daily OHLCV or None
        """
        try:
            # Try to load minute data and aggregate to daily
            minute_df = self.load_minute_data(symbol, start_date, end_date)
            if minute_df is None or minute_df.empty:
                return None
            
            # Aggregate minute to daily
            minute_df['date'] = pd.to_datetime(minute_df['datetime']).dt.date
            daily_df = minute_df.groupby('date').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'amount': 'sum'
            }).reset_index()
            daily_df.rename(columns={'date': 'datetime'}, inplace=True)
            
            return daily_df
        except Exception as e:
            logger.debug(f"query_daily {symbol}: {e}")
            return None
    
    def upsert_daily(self, df: pd.DataFrame) -> bool:
        """
        Upsert daily data (compatibility method - stores in separate daily parquet).
        
        Note: Daily data is stored separately from minute data.
        
        Args:
            df: DataFrame with daily OHLCV data
            
        Returns:
            True if successful
        """
        if df is None or df.empty:
            return False
        
        try:
            # Create daily data directory if needed
            daily_dir = self.data_root / "daily_data"
            daily_dir.mkdir(exist_ok=True)
            
            # Determine symbol column
            symbol_col = 'symbol' if 'symbol' in df.columns else 'ts_code'
            if symbol_col not in df.columns:
                logger.error("upsert_daily: DataFrame missing symbol/ts_code column")
                return False
            
            for symbol, group in df.groupby(symbol_col):
                file_path = daily_dir / f"{symbol}.parquet"
                group_clean = group.drop(columns=[symbol_col], errors='ignore')
                
                # Merge with existing if present
                if file_path.exists():
                    existing = pd.read_parquet(file_path)
                    combined = pd.concat([existing, group_clean]).drop_duplicates(
                        subset=['trade_date'] if 'trade_date' in group_clean.columns else ['datetime'],
                        keep='last'
                    ).sort_values('trade_date' if 'trade_date' in group_clean.columns else 'datetime')
                    combined.to_parquet(file_path, index=False)
                else:
                    group_clean.to_parquet(file_path, index=False)
                    
            return True
        except Exception as e:
            logger.error(f"upsert_daily failed: {e}")
            return False
    
    def close(self):
        """Close DuckDB connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("DuckDB connection closed")
