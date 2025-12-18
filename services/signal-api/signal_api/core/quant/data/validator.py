"""
AI Quant Platform - Data Validator
Ensures data integrity and quality for minute-level market data.

Features:
- Completeness check (240 bars per day)
- Continuity check (no gaps in timeline)
- Anomaly detection (price spikes, zero volume)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DataValidator:
    """
    Validates minute-level market data quality.
    
    Validation Rules:
    1. Completeness: Each trading day should have 240-241 bars
    2. Continuity: No gaps in the datetime sequence
    3. Sanity: No extreme price movements (>20% intraday)
    4. Volume: No zero-volume periods during trading hours
    """
    
    # Expected bars per trading day (A-shares: 9:30-11:30, 13:00-15:00)
    EXPECTED_BARS_MIN = 240
    EXPECTED_BARS_MAX = 242  # Allow slight variance
    
    # Maximum allowed intraday price change
    MAX_INTRADAY_CHANGE = 0.22  # 22% for ChiNext/STAR boards
    
    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: If True, raise exception on validation failure.
                         If False, log warning and continue.
        """
        self.strict_mode = strict_mode
        self.validation_errors: List[Dict] = []
    
    def validate(self, df: pd.DataFrame, symbol: str) -> Tuple[bool, List[Dict]]:
        """
        Run all validation checks on a DataFrame.
        
        Args:
            df: DataFrame with minute bars
            symbol: Stock symbol for logging
        
        Returns:
            (is_valid, list_of_errors)
        """
        self.validation_errors = []
        
        if df.empty:
            self._add_error(symbol, "EMPTY_DATA", "DataFrame is empty")
            return False, self.validation_errors
        
        # Ensure datetime column exists and is proper type
        if 'datetime' not in df.columns:
            self._add_error(symbol, "MISSING_COLUMN", "Missing 'datetime' column")
            return False, self.validation_errors
        
        df = df.copy()
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')
        
        # Run individual checks
        self._check_completeness(df, symbol)
        self._check_continuity(df, symbol)
        self._check_price_sanity(df, symbol)
        self._check_volume_sanity(df, symbol)
        
        is_valid = len(self.validation_errors) == 0
        
        if not is_valid:
            msg = f"Validation failed for {symbol}: {len(self.validation_errors)} errors"
            if self.strict_mode:
                raise DataValidationError(msg)
            else:
                logger.warning(msg)
        
        return is_valid, self.validation_errors
    
    def _add_error(self, symbol: str, error_type: str, message: str, details: Optional[Dict] = None):
        """Record a validation error."""
        error = {
            "symbol": symbol,
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.validation_errors.append(error)
        logger.warning(f"[{symbol}] {error_type}: {message}")
    
    def _check_completeness(self, df: pd.DataFrame, symbol: str):
        """Check if each trading day has expected number of bars."""
        df['date'] = df['datetime'].dt.date
        daily_counts = df.groupby('date').size()
        
        for date, count in daily_counts.items():
            if count < self.EXPECTED_BARS_MIN:
                self._add_error(
                    symbol,
                    "INCOMPLETE_DAY",
                    f"Date {date} has only {count} bars (expected {self.EXPECTED_BARS_MIN}+)",
                    {"date": str(date), "actual_count": count}
                )
            elif count > self.EXPECTED_BARS_MAX:
                self._add_error(
                    symbol,
                    "EXCESS_BARS",
                    f"Date {date} has {count} bars (expected max {self.EXPECTED_BARS_MAX})",
                    {"date": str(date), "actual_count": count}
                )
    
    def _check_continuity(self, df: pd.DataFrame, symbol: str):
        """Check for gaps in the datetime sequence."""
        # Calculate time differences between consecutive bars
        time_diffs = df['datetime'].diff()
        
        # Expected gaps: 1 minute within session, ~90 minutes for lunch break
        # Allow up to 120 minutes to account for edge cases
        MAX_GAP_MINUTES = 120
        
        large_gaps = time_diffs[time_diffs > pd.Timedelta(minutes=MAX_GAP_MINUTES)]
        
        if not large_gaps.empty:
            for idx in large_gaps.index:
                gap_start = df.loc[idx - 1, 'datetime'] if idx > 0 else None
                gap_end = df.loc[idx, 'datetime']
                gap_duration = time_diffs[idx]
                
                # Skip if it's an overnight gap
                if gap_start and gap_start.date() != gap_end.date():
                    continue
                
                self._add_error(
                    symbol,
                    "DATA_GAP",
                    f"Gap detected: {gap_duration} at {gap_end}",
                    {"gap_start": str(gap_start), "gap_end": str(gap_end)}
                )
    
    def _check_price_sanity(self, df: pd.DataFrame, symbol: str):
        """Check for unrealistic price movements."""
        df['date'] = df['datetime'].dt.date
        
        for date, group in df.groupby('date'):
            if len(group) < 2:
                continue
            
            # Calculate intraday high-low range
            day_high = group['high'].max()
            day_low = group['low'].min()
            
            if day_low > 0:
                intraday_range = (day_high - day_low) / day_low
                
                if intraday_range > self.MAX_INTRADAY_CHANGE:
                    self._add_error(
                        symbol,
                        "EXTREME_PRICE_MOVE",
                        f"Intraday range {intraday_range:.2%} exceeds {self.MAX_INTRADAY_CHANGE:.0%}",
                        {"date": str(date), "high": day_high, "low": day_low}
                    )
    
    def _check_volume_sanity(self, df: pd.DataFrame, symbol: str):
        """Check for suspicious zero-volume periods."""
        # Count zero-volume bars (excluding first bar which might be auction)
        zero_volume_mask = (df['volume'] == 0) | (df['volume'].isna())
        zero_volume_count = zero_volume_mask.sum()
        
        # Allow up to 5% of bars to have zero volume (suspension, halt)
        max_allowed = len(df) * 0.05
        
        if zero_volume_count > max_allowed:
            self._add_error(
                symbol,
                "EXCESSIVE_ZERO_VOLUME",
                f"{zero_volume_count} bars have zero volume (max allowed: {max_allowed:.0f})",
                {"zero_volume_count": int(zero_volume_count)}
            )
