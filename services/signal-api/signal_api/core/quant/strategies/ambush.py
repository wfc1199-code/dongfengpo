"""
AI Quant Platform - Ambush Strategy (潜伏策略)
Identifies stocks with potential for overnight gains based on washout patterns.

Entry Criteria:
1. Low intraday volatility (< 6%)
2. High volume ratio (accumulation pattern)
3. Bollinger Band squeeze (low volatility)
4. Short-term washout with OBV divergence

Exit Criteria:
1. Next day gap up or intraday breakout
2. Stop loss at -3%
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import pandas as pd
import numpy as np
import logging

from .base import BaseStrategy, StrategyConfig, Signal, SignalType

logger = logging.getLogger(__name__)


@dataclass
class AmbushConfig(StrategyConfig):
    """Configuration for Ambush Strategy."""
    name: str = "AmbushStrategy"
    lookback_days: int = 30
    min_confidence: float = 0.65
    
    # Volume criteria
    volume_ratio_min: float = 1.5  # Minimum volume ratio vs 20-day average
    volume_ratio_max: float = 5.0  # Maximum (avoid pump)
    
    # Volatility criteria
    max_intraday_range: float = 0.06  # Max daily range (6%)
    bollinger_squeeze_threshold: float = 0.03  # Band width threshold
    
    # Washout criteria
    washout_days: int = 5  # Days of price decline
    min_washout_pct: float = 0.05  # Minimum decline (5%)
    max_washout_pct: float = 0.15  # Maximum decline (15%)
    
    # OBV divergence
    obv_divergence_threshold: float = 0.1  # 10% divergence


class AmbushStrategy(BaseStrategy):
    """
    Ambush Strategy (潜伏策略)
    
    Identifies stocks showing signs of accumulation during a pullback:
    - Price is declining but volume is accumulating (OBV divergence)
    - Volatility is contracting (Bollinger squeeze)
    - Volume ratio elevated but not extreme
    
    These patterns often precede a breakout in the next 1-3 days.
    """
    
    def __init__(self, config: Optional[AmbushConfig] = None):
        super().__init__(config or AmbushConfig())
        self.config: AmbushConfig = self.config  # Type hint
    
    @staticmethod
    def _calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Calculate On-Balance Volume correctly.
        
        OBV = Previous OBV + (Volume if close > prev_close, -Volume if close < prev_close, 0 if equal)
        """
        obv = pd.Series(0.0, index=close.index)
        price_change = close.diff()
        
        for i in range(1, len(close)):
            if price_change.iloc[i] > 0:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif price_change.iloc[i] < 0:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    def calculate_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all factors for the Ambush Strategy.
        
        Factors:
        - volume_ratio: Volume / 20-day MA
        - intraday_range: (High - Low) / Close
        - bollinger_width: (Upper - Lower) / Middle band
        - washout_pct: % decline over washout period
        - obv: On-Balance Volume
        - obv_divergence: OBV trend vs price trend
        """
        df = df.copy()
        
        if 'symbol' not in df.columns:
            df['symbol'] = 'UNKNOWN'
            
        def calc_stock_factors(group):
            # Volume Ratio
            group['volume_ma20'] = group['volume'].rolling(20, min_periods=20).mean()
            group['volume_ratio'] = group['volume'] / (group['volume_ma20'] + 1e-9)
            
            # Intraday Range
            group['intraday_range'] = (group['high'] - group['low']) / (group['close'] + 1e-9)
            
            # Bollinger Bands
            group['sma20'] = group['close'].rolling(20, min_periods=20).mean()
            group['std20'] = group['close'].rolling(20, min_periods=20).std()
            group['bb_upper'] = group['sma20'] + 2 * group['std20']
            group['bb_lower'] = group['sma20'] - 2 * group['std20']
            group['bb_width'] = (group['bb_upper'] - group['bb_lower']) / (group['sma20'] + 1e-9)
            
            # Washout
            washout_days = self.config.washout_days
            group['price_change_n'] = group['close'].pct_change(washout_days)
            
            # OBV - vectorized
            price_diff = group['close'].diff()
            direction = np.zeros(len(group))
            direction[price_diff > 0] = 1
            direction[price_diff < 0] = -1
            group['obv'] = (direction * group['volume']).cumsum()
            
            # Slopes
            group['obv_slope'] = group['obv'].rolling(washout_days, min_periods=washout_days).apply(
                lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) >= washout_days else 0,
                raw=True
            )
            group['price_slope'] = group['close'].rolling(washout_days, min_periods=washout_days).apply(
                lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) >= washout_days else 0,
                raw=True
            )
            
            # OBV Divergence
            group['obv_divergence'] = (
                (group['obv_slope'] > 0) & (group['price_slope'] < 0)
            ).astype(int)
            
            # Relative position
            group['price_min5'] = group['low'].rolling(5, min_periods=5).min()
            group['price_max5'] = group['high'].rolling(5, min_periods=5).max()
            group['relative_pos'] = (group['close'] - group['price_min5']) / (group['price_max5'] - group['price_min5'] + 1e-9)
            
            return group
            
        df = df.groupby('symbol', group_keys=False).apply(calc_stock_factors)
        
        # Sort by datetime to ensure alignment with engine
        df = df.sort_values(['datetime', 'symbol']).reset_index(drop=True)
        
        return df
    
    def generate_signal(self, index: int) -> Optional[Signal]:
        """
        Generate buy signal if ambush conditions are met.
        
        Conditions:
        1. Volume ratio within range (accumulation, not pump)
        2. Low intraday volatility (squeeze)
        3. Price in washout zone (declined but not crashed)
        4. OBV divergence (smart money accumulating)
        """
        if self._factors is None or index < self.config.lookback_days:
            return None
        
        row = self._factors.iloc[index]
        
        # Check for NaN values
        if pd.isna(row['volume_ratio']) or pd.isna(row['bb_width']):
            return None
        
        # Factor checks
        checks = {}
        
        # 1. Volume ratio in range
        vol_ratio = row['volume_ratio']
        checks['volume_in_range'] = (
            self.config.volume_ratio_min <= vol_ratio <= self.config.volume_ratio_max
        )
        
        # 2. Low volatility (Bollinger squeeze)
        bb_width = row['bb_width']
        checks['bollinger_squeeze'] = bb_width < self.config.bollinger_squeeze_threshold
        
        # 3. Intraday range is low
        intraday = row['intraday_range']
        checks['low_volatility'] = intraday < self.config.max_intraday_range
        
        # 4. In washout zone (price declined but not crashed)
        washout = abs(row['price_change_n']) if pd.notna(row['price_change_n']) else 0
        checks['washout_zone'] = (
            self.config.min_washout_pct <= washout <= self.config.max_washout_pct
        )
        
        # 5. OBV divergence (smart money accumulating)
        checks['obv_divergence'] = row['obv_divergence'] == 1
        
        # Calculate confidence based on how many checks pass
        passed_checks = sum(checks.values())
        total_checks = len(checks)
        base_confidence = passed_checks / total_checks
        
        # Boost confidence if OBV divergence is present (key signal)
        if checks['obv_divergence']:
            base_confidence = min(1.0, base_confidence + 0.15)
        
        # Only generate signal if enough conditions are met
        if passed_checks < 3:
            return None
        
        # Build reason string
        reasons = []
        if checks['volume_in_range']:
            reasons.append(f"量比{vol_ratio:.1f}")
        if checks['bollinger_squeeze']:
            reasons.append("布林收窄")
        if checks['washout_zone']:
            reasons.append(f"回调{washout:.1%}")
        if checks['obv_divergence']:
            reasons.append("OBV背离")
        
        return Signal(
            symbol=self._data.iloc[index].get('symbol', 'UNKNOWN'),
            signal_type=SignalType.BUY,
            confidence=round(base_confidence, 2),
            price=row['close'],
            timestamp=pd.to_datetime(row['datetime']),
            reason="潜伏信号: " + ", ".join(reasons),
            factors={
                "volume_ratio": round(vol_ratio, 2),
                "bb_width": round(bb_width, 4),
                "washout_pct": round(washout, 4),
                "obv_divergence": int(checks['obv_divergence']),
                "relative_pos": round(row['relative_pos'], 2) if pd.notna(row['relative_pos']) else 0
            }
        )
