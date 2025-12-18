"""
AI Quant Platform - Ignition Strategy (点火策略)
Identifies intraday breakout candidates with volume surge.

Entry Criteria:
1. Rapid volume increase (分时量比 > 3)
2. Price breakout above key level (布林上轨 or 5日高点)
3. From "Tomorrow's Potential" pool (前一日潜伏池)
4. Morning session preferred (9:30 - 11:00)

Exit Criteria:
1. Intraday momentum fade
2. Stop loss at -3%
3. EOD if no follow-through
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Dict
import pandas as pd
import numpy as np
import logging

from .base import BaseStrategy, StrategyConfig, Signal, SignalType

logger = logging.getLogger(__name__)


@dataclass
class IgnitionConfig(StrategyConfig):
    """Configuration for Ignition Strategy."""
    name: str = "IgnitionStrategy"
    lookback_days: int = 5  # Short lookback for intraday
    min_confidence: float = 0.7
    
    # Volume criteria
    minute_volume_ratio_min: float = 3.0  # 分时量比最小值
    cumulative_volume_ratio_min: float = 1.5  # 累计量比最小值
    
    # Breakout criteria
    breakout_threshold: float = 0.02  # 突破幅度最小 2%
    
    # Time window (trading hours)
    preferred_start_time: str = "09:30"
    preferred_end_time: str = "11:00"
    
    # Stop loss
    stop_loss_pct: float = 0.03  # 3%


class IgnitionStrategy(BaseStrategy):
    """
    Ignition Strategy (点火策略)
    
    Real-time intraday strategy for catching momentum breakouts:
    - Monitors minute-level volume surges
    - Identifies price breakouts above resistance
    - Best used on stocks from the "Ambush" pool
    
    This strategy is designed for minute-bar data.
    """
    
    def __init__(self, config: Optional[IgnitionConfig] = None):
        super().__init__(config or IgnitionConfig())
        self.config: IgnitionConfig = self.config
        
        # Parse time boundaries
        self._start_time = datetime.strptime(self.config.preferred_start_time, "%H:%M").time()
        self._end_time = datetime.strptime(self.config.preferred_end_time, "%H:%M").time()
    
    def calculate_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate intraday factors for Ignition Strategy.
        
        Factors:
        - minute_volume_ratio: Current minute volume / average minute volume
        - cumulative_volume_ratio: Cumulative volume / expected volume at this time
        - price_vs_high5: Current price vs 5-day high
        - price_vs_bb_upper: Current price vs Bollinger upper band
        - momentum: Short-term price momentum
        """
        df = df.copy()
        
        # Ensure datetime is proper type
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['time'] = df['datetime'].dt.time
        df['date'] = df['datetime'].dt.date
        
        if 'symbol' not in df.columns:
            df['symbol'] = 'UNKNOWN'
            
        # Helper to calculate factors for a single stock
        def calc_stock_factors(group):
            # Average minute volume (rolling 20 bars)
            group['volume_ma20'] = group['volume'].rolling(20, min_periods=20).mean()
            group['minute_volume_ratio'] = group['volume'] / (group['volume_ma20'] + 1e-9)
            
            # Cumulative volume for the day
            group['daily_volume'] = group.groupby('date')['volume'].cumsum()
            
            # 5-day high (daily aggregation)
            daily_highs = group.groupby('date')['high'].max()
            daily_high5 = daily_highs.rolling(5, min_periods=1).max()
            group['high5'] = group['date'].map(daily_high5)
            
            # Price vs 5-day high
            group['price_vs_high5'] = (group['close'] - group['high5']) / (group['high5'] + 1e-9)
            
            # Bollinger Bands (20-minute)
            group['sma20'] = group['close'].rolling(20, min_periods=20).mean()
            group['std20'] = group['close'].rolling(20, min_periods=20).std()
            group['bb_upper'] = group['sma20'] + 2 * group['std20']
            group['price_vs_bb'] = (group['close'] - group['bb_upper']) / (group['bb_upper'] + 1e-9)
            
            # Short-term momentum (5-bar)
            group['momentum5'] = group['close'].pct_change(5)
            
            # VWAP
            group['pv'] = group['close'] * group['volume']
            group['cumulative_pv'] = group.groupby('date')['pv'].cumsum()
            group['cumulative_vol'] = group.groupby('date')['volume'].cumsum()
            group['vwap'] = group['cumulative_pv'] / (group['cumulative_vol'] + 1e-9)
            group['price_vs_vwap'] = (group['close'] - group['vwap']) / (group['vwap'] + 1e-9)
            
            return group
            
        # Apply per stock
        df = df.groupby('symbol', group_keys=False).apply(calc_stock_factors)
        
        # Sort by datetime to ensure alignment with engine (CRITICAL for multi-stock)
        df = df.sort_values(['datetime', 'symbol']).reset_index(drop=True)
        
        # Clean up
        df.drop(columns=['pv', 'cumulative_pv', 'cumulative_vol'], inplace=True, errors='ignore')
        
        return df
    
    def _is_preferred_time(self, t: time) -> bool:
        """Check if current time is in preferred trading window."""
        if t is None or pd.isna(t):
            return False
        # Convert to minutes for accurate comparison
        t_minutes = t.hour * 60 + t.minute
        start_minutes = self._start_time.hour * 60 + self._start_time.minute
        end_minutes = self._end_time.hour * 60 + self._end_time.minute
        return start_minutes <= t_minutes <= end_minutes
    
    def generate_signal(self, index: int) -> Optional[Signal]:
        """
        Generate buy signal if ignition conditions are met.
        
        Conditions:
        1. Minute volume ratio surge (hot money entering)
        2. Price breaking above resistance
        3. In preferred time window
        4. Positive momentum
        """
        if self._factors is None or index < 20:  # Need 20 bars minimum
            return None
        
        row = self._factors.iloc[index]
        
        # Check for NaN values
        if pd.isna(row['minute_volume_ratio']) or pd.isna(row['bb_upper']):
            return None
        
        checks = {}
        
        # 1. Volume surge
        vol_ratio = row['minute_volume_ratio']
        checks['volume_surge'] = vol_ratio >= self.config.minute_volume_ratio_min
        
        # 2. Price breakout (above BB upper or 5-day high)
        price_vs_bb = row['price_vs_bb'] if pd.notna(row['price_vs_bb']) else -1
        price_vs_high5 = row['price_vs_high5'] if pd.notna(row['price_vs_high5']) else -1
        checks['price_breakout'] = (
            price_vs_bb > 0 or  # Above BB upper
            price_vs_high5 >= 0  # At or above 5-day high
        )
        
        # 3. Preferred time window
        current_time = row['time'] if pd.notna(row['time']) else time(12, 0)
        checks['good_timing'] = self._is_preferred_time(current_time)
        
        # 4. Positive momentum
        momentum = row['momentum5'] if pd.notna(row['momentum5']) else 0
        checks['positive_momentum'] = momentum > self.config.breakout_threshold
        
        # 5. Above VWAP (institutional support)
        price_vs_vwap = row['price_vs_vwap'] if pd.notna(row['price_vs_vwap']) else -1
        checks['above_vwap'] = price_vs_vwap > 0
        
        # Calculate confidence
        passed_checks = sum(checks.values())
        total_checks = len(checks)
        
        # Must have volume surge and breakout at minimum
        if not (checks['volume_surge'] and checks['price_breakout']):
            return None
        
        base_confidence = passed_checks / total_checks
        
        # Boost for morning session
        if checks['good_timing']:
            base_confidence = min(1.0, base_confidence + 0.1)
        
        # Build reason
        reasons = []
        if checks['volume_surge']:
            reasons.append(f"量比{vol_ratio:.1f}")
        if price_vs_bb > 0:
            reasons.append("突破布林")
        if price_vs_high5 >= 0:
            reasons.append("创5日新高")
        if checks['above_vwap']:
            reasons.append("站上VWAP")
        if checks['good_timing']:
            reasons.append("黄金时段")
        
        return Signal(
            symbol=self._data.iloc[index].get('symbol', 'UNKNOWN'),
            signal_type=SignalType.BUY,
            confidence=round(base_confidence, 2),
            price=row['close'],
            timestamp=pd.to_datetime(row['datetime']),
            reason="点火信号: " + ", ".join(reasons),
            factors={
                "minute_volume_ratio": round(vol_ratio, 2),
                "price_vs_bb": round(price_vs_bb, 4),
                "price_vs_high5": round(price_vs_high5, 4),
                "momentum5": round(momentum, 4),
                "price_vs_vwap": round(price_vs_vwap, 4)
            }
        )
