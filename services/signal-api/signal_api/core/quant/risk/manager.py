"""
AI Quant Platform - Risk Manager
Enterprise-grade risk management with hard stop-loss and circuit breaker.

Features:
- Single trade stop-loss (3%)
- Daily drawdown circuit breaker (5%)
- Position sizing limits (20% per stock)
- Sector concentration limits (3 stocks max)
- Thread-safe operations
"""

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional, Set, Deque
from enum import Enum

logger = logging.getLogger(__name__)

# Tolerance for floating point comparisons
FLOAT_TOLERANCE = 1e-9


class RiskAction(Enum):
    """Actions the risk manager can take."""
    ALLOW = "allow"
    REJECT_STOP_LOSS = "reject_stop_loss"
    REJECT_CIRCUIT_BREAKER = "reject_circuit_breaker"
    REJECT_POSITION_LIMIT = "reject_position_limit"
    REJECT_SECTOR_LIMIT = "reject_sector_limit"
    REJECT_CONCURRENT_SIGNALS = "reject_concurrent_signals"
    REJECT_INVALID_INPUT = "reject_invalid_input"


@dataclass
class Position:
    """Represents a single stock position."""
    symbol: str
    entry_price: float
    quantity: int
    entry_time: datetime
    sector: str = ""
    current_price: float = 0.0
    
    @property
    def market_value(self) -> float:
        return self.current_price * self.quantity
    
    @property
    def pnl_percent(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price


@dataclass
class RiskConfig:
    """Risk management configuration parameters."""
    # Stop-loss: close position if loss exceeds this threshold
    single_trade_stop_loss: float = 0.03  # 3%
    
    # Circuit breaker: stop all buying if daily drawdown exceeds this
    daily_drawdown_limit: float = 0.05  # 5%
    
    # Position sizing: max allocation to single stock
    max_single_position_pct: float = 0.20  # 20%
    
    # Sector concentration: max stocks from same sector
    max_sector_stocks: int = 3
    
    # Signal throttling: max signals to act on per second
    max_concurrent_signals: int = 2
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0 < self.single_trade_stop_loss < 1:
            raise ValueError(f"single_trade_stop_loss must be between 0 and 1, got {self.single_trade_stop_loss}")
        if not 0 < self.daily_drawdown_limit < 1:
            raise ValueError(f"daily_drawdown_limit must be between 0 and 1, got {self.daily_drawdown_limit}")
        if not 0 < self.max_single_position_pct <= 1:
            raise ValueError(f"max_single_position_pct must be between 0 and 1, got {self.max_single_position_pct}")
        if self.max_sector_stocks < 1:
            raise ValueError(f"max_sector_stocks must be >= 1, got {self.max_sector_stocks}")
        if self.max_concurrent_signals < 1:
            raise ValueError(f"max_concurrent_signals must be >= 1, got {self.max_concurrent_signals}")


@dataclass
class RiskCheckResult:
    """Result of a risk check."""
    action: RiskAction
    message: str
    details: Dict = field(default_factory=dict)
    
    @property
    def is_allowed(self) -> bool:
        return self.action == RiskAction.ALLOW


class RiskManager:
    """
    Enterprise-grade risk management system.
    
    Implements:
    1. Pre-trade checks (before opening position)
    2. Real-time monitoring (during position)
    3. Post-trade logging (audit trail)
    
    Thread Safety:
        All public methods are protected by a reentrant lock.
    """
    
    def __init__(self, config: Optional[RiskConfig] = None, initial_capital: float = 1_000_000):
        # Validate initial capital
        if initial_capital <= 0:
            raise ValueError(f"initial_capital must be positive, got {initial_capital}")
        
        self.config = config or RiskConfig()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Thread safety: reentrant lock for all state access
        self._lock = threading.RLock()
        
        # Position tracking
        self.positions: Dict[str, Position] = {}
        
        # Daily tracking
        self.daily_high_watermark: float = initial_capital
        self.daily_pnl: float = 0.0
        self.trading_date: Optional[date] = None
        
        # Signal throttling using sliding window
        self._signal_timestamps: Deque[datetime] = deque()
        
        # Circuit breaker state
        self.circuit_breaker_active: bool = False
        
        logger.info(f"RiskManager initialized with capital: {initial_capital:,.0f}")
    
    def reset_daily(self):
        """Reset daily counters at market open."""
        with self._lock:
            today = date.today()
            if self.trading_date != today:
                self.trading_date = today
                self.daily_high_watermark = self.current_capital
                self.daily_pnl = 0.0
                self.circuit_breaker_active = False
                self._signal_timestamps.clear()
                logger.info(f"Daily reset for {today}")
    
    def update_prices(self, prices: Dict[str, float]) -> List[str]:
        """
        Update current prices and check for stop-loss triggers.
        
        Args:
            prices: Dict mapping symbol to current price
        
        Returns:
            List of symbols that should be stop-lossed.
        """
        with self._lock:
            stop_loss_symbols = []
            
            for symbol, position in self.positions.items():
                if symbol in prices:
                    price = prices[symbol]
                    if price <= 0:
                        logger.warning(f"Invalid price {price} for {symbol}, skipping")
                        continue
                    
                    position.current_price = price
                    
                    # Check stop-loss using safe comparison
                    pnl = position.pnl_percent
                    threshold = -self.config.single_trade_stop_loss
                    
                    if self._compare_float(pnl, threshold) < 0:
                        logger.warning(
                            f"STOP-LOSS triggered for {symbol}: "
                            f"PnL={pnl:.2%}, "
                            f"Threshold={threshold:.2%}"
                        )
                        stop_loss_symbols.append(symbol)
            
            # Update portfolio value and check circuit breaker
            self._update_portfolio_value()
            
            return stop_loss_symbols
    
    @staticmethod
    def _compare_float(a: float, b: float, tolerance: float = FLOAT_TOLERANCE) -> int:
        """Compare floats with tolerance. Returns -1, 0, or 1."""
        diff = a - b
        if abs(diff) < tolerance:
            return 0
        return -1 if diff < 0 else 1
    
    def _update_portfolio_value(self):
        """Update portfolio value and check circuit breaker. Must hold lock."""
        position_value = sum(p.market_value for p in self.positions.values())
        entry_cost = sum(p.entry_price * p.quantity for p in self.positions.values())
        self.current_capital = self.initial_capital + position_value - entry_cost
        
        # Update high watermark
        if self.current_capital > self.daily_high_watermark:
            self.daily_high_watermark = self.current_capital
        
        # Check circuit breaker (with division by zero protection)
        drawdown = self._get_drawdown_unsafe()
        
        if self._compare_float(drawdown, self.config.daily_drawdown_limit) > 0:
            if not self.circuit_breaker_active:
                logger.error(
                    f"CIRCUIT BREAKER activated: "
                    f"Drawdown={drawdown:.2%}, "
                    f"Limit={self.config.daily_drawdown_limit:.2%}"
                )
                self.circuit_breaker_active = True
    
    def _get_drawdown_unsafe(self) -> float:
        """Calculate drawdown without lock. Internal use only."""
        if self.daily_high_watermark <= 0:
            return 0.0
        return (self.daily_high_watermark - self.current_capital) / self.daily_high_watermark
    
    def check_buy_signal(
        self,
        symbol: str,
        proposed_value: float,
        sector: str = ""
    ) -> RiskCheckResult:
        """
        Check if a buy signal should be allowed.
        
        Args:
            symbol: Stock symbol
            proposed_value: Proposed position value
            sector: Stock sector for concentration check
        
        Returns:
            RiskCheckResult with action and message.
        """
        with self._lock:
            # Input validation
            if not symbol or not isinstance(symbol, str):
                return RiskCheckResult(
                    action=RiskAction.REJECT_INVALID_INPUT,
                    message=f"Invalid symbol: {symbol}",
                    details={"symbol": symbol}
                )
            
            if proposed_value <= 0:
                return RiskCheckResult(
                    action=RiskAction.REJECT_INVALID_INPUT,
                    message=f"Proposed value must be positive: {proposed_value}",
                    details={"proposed_value": proposed_value}
                )
            
            if proposed_value > self.initial_capital:
                return RiskCheckResult(
                    action=RiskAction.REJECT_POSITION_LIMIT,
                    message=f"Proposed value {proposed_value:,.0f} exceeds initial capital {self.initial_capital:,.0f}",
                    details={"proposed_value": proposed_value, "initial_capital": self.initial_capital}
                )
            
            # Check circuit breaker
            if self.circuit_breaker_active:
                return RiskCheckResult(
                    action=RiskAction.REJECT_CIRCUIT_BREAKER,
                    message="Circuit breaker active - no new positions allowed today",
                    details={"daily_drawdown": self._get_drawdown_unsafe()}
                )
            
            # Check position size limit using Decimal for precision
            position_pct = Decimal(str(proposed_value)) / Decimal(str(self.initial_capital))
            limit_pct = Decimal(str(self.config.max_single_position_pct))
            
            if position_pct > limit_pct:
                return RiskCheckResult(
                    action=RiskAction.REJECT_POSITION_LIMIT,
                    message=f"Position size {float(position_pct):.1%} exceeds {float(limit_pct):.0%} limit",
                    details={"proposed_pct": float(position_pct), "limit": float(limit_pct)}
                )
            
            # Check sector concentration
            if sector:
                sector_stocks = self._get_sector_stocks_unsafe(sector)
                if len(sector_stocks) >= self.config.max_sector_stocks:
                    return RiskCheckResult(
                        action=RiskAction.REJECT_SECTOR_LIMIT,
                        message=f"Sector {sector} already has {len(sector_stocks)} stocks (max: {self.config.max_sector_stocks})",
                        details={"sector": sector, "existing_stocks": list(sector_stocks)}
                    )
            
            # Check signal throttling using sliding window
            now = datetime.now()
            cutoff = now - timedelta(seconds=1)
            
            # Clean old timestamps
            while self._signal_timestamps and self._signal_timestamps[0] < cutoff:
                self._signal_timestamps.popleft()
            
            # Check limit
            if len(self._signal_timestamps) >= self.config.max_concurrent_signals:
                return RiskCheckResult(
                    action=RiskAction.REJECT_CONCURRENT_SIGNALS,
                    message=f"Too many signals ({len(self._signal_timestamps)}) in 1 second",
                    details={"count": len(self._signal_timestamps), "limit": self.config.max_concurrent_signals}
                )
            
            # Record this signal
            self._signal_timestamps.append(now)
            
            # All checks passed
            return RiskCheckResult(
                action=RiskAction.ALLOW,
                message="Buy signal approved",
                details={"symbol": symbol, "value": proposed_value}
            )
    
    def _get_drawdown(self) -> float:
        """Calculate current drawdown from daily high. Thread-safe."""
        with self._lock:
            return self._get_drawdown_unsafe()
    
    def _get_sector_stocks_unsafe(self, sector: str) -> Set[str]:
        """Get symbols of stocks in a specific sector. Must hold lock."""
        return {
            symbol for symbol, pos in self.positions.items()
            if pos.sector == sector
        }
    
    def add_position(self, position: Position):
        """Record a new position."""
        with self._lock:
            if not position.symbol:
                raise ValueError("Position must have a valid symbol")
            self.positions[position.symbol] = position
            logger.info(f"Position added: {position.symbol} @ {position.entry_price:.2f} x {position.quantity}")
    
    def remove_position(self, symbol: str) -> Optional[Position]:
        """Remove a closed position."""
        with self._lock:
            if symbol in self.positions:
                position = self.positions.pop(symbol)
                logger.info(f"Position closed: {symbol}, PnL: {position.pnl_percent:.2%}")
                return position
            return None
    
    def get_status(self) -> Dict:
        """Get current risk status summary."""
        with self._lock:
            return {
                "capital": self.current_capital,
                "daily_high": self.daily_high_watermark,
                "drawdown": self._get_drawdown_unsafe(),
                "circuit_breaker_active": self.circuit_breaker_active,
                "position_count": len(self.positions),
                "positions": {
                    symbol: {
                        "entry_price": p.entry_price,
                        "current_price": p.current_price,
                        "pnl_pct": p.pnl_percent,
                        "sector": p.sector
                    }
                    for symbol, p in self.positions.items()
                }
            }
