"""
AI Quant Platform - Realtime Engine
Real-time trading engine with simulation and live modes.

Features:
- AkShare realtime data integration
- Simulation mode (paper trading)
- Signal queue management
- Risk-aware execution
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import pandas as pd

from ..strategies.base import BaseStrategy, Signal, SignalType
from ..risk.manager import RiskManager, RiskConfig, Position, RiskAction

logger = logging.getLogger(__name__)


class EngineMode(Enum):
    """Realtime engine operating modes."""
    SIMULATION = "simulation"  # Paper trading, no real orders
    LIVE = "live"  # Real trading (requires broker integration)


@dataclass
class ExecutionResult:
    """Result of attempting to execute a signal."""
    signal: Signal
    success: bool
    executed_price: float = 0.0
    executed_quantity: int = 0
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.signal.symbol,
            "signal_type": self.signal.signal_type.value,
            "success": self.success,
            "executed_price": self.executed_price,
            "executed_quantity": self.executed_quantity,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class RealtimeConfig:
    """Configuration for realtime engine."""
    mode: EngineMode = EngineMode.SIMULATION
    initial_capital: float = 1_000_000
    position_size_pct: float = 0.1  # 10% per position
    max_positions: int = 5
    polling_interval_seconds: float = 3.0  # AkShare refresh interval
    
    # Trading hours (A-share)
    trading_start: time = time(9, 30)
    trading_end: time = time(15, 0)
    
    # Simulation settings
    simulated_slippage_pct: float = 0.001  # 0.1%
    simulated_commission_rate: float = 0.0003  # 万三


class RealtimeEngine:
    """
    Real-time trading engine for live signal monitoring and execution.
    
    Supports two modes:
    - SIMULATION: Paper trading for testing strategies
    - LIVE: Real trading (requires broker API integration)
    
    Usage:
        async with RealtimeEngine(config, strategy) as engine:
            await engine.start(['000001', '600000'])
    """
    
    def __init__(
        self,
        config: Optional[RealtimeConfig] = None,
        strategy: Optional[BaseStrategy] = None,
        risk_manager: Optional[RiskManager] = None
    ):
        self.config = config or RealtimeConfig()
        self.strategy = strategy
        self.risk_manager = risk_manager or RiskManager(
            initial_capital=self.config.initial_capital
        )
        
        # State
        self._running = False
        self._stop_event: Optional[asyncio.Event] = None
        self._capital = self.config.initial_capital
        self._positions: Dict[str, Position] = {}
        self._pending_signals: List[Signal] = []
        self._execution_history: List[ExecutionResult] = []
        
        # Data cache
        self._latest_prices: Dict[str, float] = {}
        self._latest_data: Optional[pd.DataFrame] = None
        
        # Callbacks
        self._on_signal_callback: Optional[Callable[[Signal], None]] = None
        self._on_execution_callback: Optional[Callable[[ExecutionResult], None]] = None
        
        logger.info(f"RealtimeEngine initialized in {self.config.mode.value} mode")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures cleanup."""
        await self.stop()
        return False
    
    def set_strategy(self, strategy: BaseStrategy):
        """Set or update the strategy."""
        self.strategy = strategy
        logger.info(f"Strategy set to: {strategy.name}")
    
    def set_on_signal_callback(self, callback: Callable[[Signal], None]):
        """Set callback for when a new signal is generated."""
        self._on_signal_callback = callback
    
    def set_on_execution_callback(self, callback: Callable[[ExecutionResult], None]):
        """Set callback for when a signal is executed."""
        self._on_execution_callback = callback
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        now = datetime.now().time()
        
        # Morning session: 9:30 - 11:30
        morning_start = self.config.trading_start
        morning_end = time(11, 30)
        
        # Afternoon session: 13:00 - 15:00
        afternoon_start = time(13, 0)
        afternoon_end = self.config.trading_end
        
        # Check if in morning or afternoon session
        in_morning = morning_start <= now <= morning_end
        in_afternoon = afternoon_start <= now <= afternoon_end
        
        return in_morning or in_afternoon
    
    async def start(self, symbols: List[str]):
        """
        Start the realtime engine.
        
        Args:
            symbols: List of stock symbols to monitor
        """
        if self._running:
            logger.warning("Engine already running")
            return
        
        if not self.strategy:
            raise RuntimeError("No strategy set. Call set_strategy() first.")
        
        self._running = True
        self._stop_event = asyncio.Event()
        logger.info(f"Starting realtime engine for {len(symbols)} symbols")
        
        # Reset daily counters
        self.risk_manager.reset_daily()
        
        # Main loop with graceful cancellation
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    if self.is_trading_hours():
                        await self._tick(symbols)
                    else:
                        logger.debug("Outside trading hours, waiting...")
                    
                    # Use wait_for to allow graceful cancellation
                    try:
                        await asyncio.wait_for(
                            self._stop_event.wait(),
                            timeout=self.config.polling_interval_seconds
                        )
                        # Event was set, stop requested
                        break
                    except asyncio.TimeoutError:
                        # Timeout is expected, continue loop
                        pass
                    
                except asyncio.CancelledError:
                    logger.info("Engine stop requested (cancelled)")
                    break
                except Exception as e:
                    logger.error(f"Error in engine loop: {e}", exc_info=True)
                    # Wait before retry, but check stop event
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=5)
                        break
                    except asyncio.TimeoutError:
                        pass
        finally:
            # Cleanup
            self._running = False
            logger.info("Realtime engine stopped")
    
    async def stop(self):
        """Stop the realtime engine gracefully."""
        if not self._running:
            return
        
        logger.info("Stopping realtime engine...")
        self._running = False
        
        # Signal stop event for immediate cancellation
        if self._stop_event:
            self._stop_event.set()
    
    async def _tick(self, symbols: List[str]):
        """Single tick of the engine loop."""
        # Fetch latest data
        data = await self._fetch_realtime_data(symbols)
        if data.empty:
            return
        
        self._latest_data = data
        
        # Update prices first
        for _, row in data.iterrows():
            symbol = row.get('symbol', row.get('code', 'UNKNOWN'))
            price = row.get('price', row.get('close', 0))
            self._latest_prices[symbol] = price
        
        # Check stop-loss BEFORE processing new signals
        # This ensures we exit losing positions before opening new ones
        stop_loss_symbols = self.risk_manager.update_prices(self._latest_prices)
        
        # Execute stop-loss orders immediately
        for symbol in stop_loss_symbols:
            await self._execute_stop_loss(symbol)
        
        # Then process new signals
        for symbol in symbols:
            # Skip if we just executed a stop-loss for this symbol
            if symbol in stop_loss_symbols:
                continue
            
            symbol_data = data[data.get('symbol', data.get('code', '')) == symbol]
            if symbol_data.empty:
                continue
            
            await self._process_symbol(symbol, symbol_data)
    
    async def _fetch_realtime_data(self, symbols: List[str]) -> pd.DataFrame:
        """
        Fetch realtime data from AkShare.
        
        In production, this would use akshare.stock_zh_a_spot_em() or similar.
        For simulation, we generate mock data.
        """
        if self.config.mode == EngineMode.SIMULATION:
            # Mock data for simulation
            import numpy as np
            data = []
            for symbol in symbols:
                base_price = self._latest_prices.get(symbol, 10.0)
                # Random walk
                price = base_price * (1 + np.random.randn() * 0.002)
                data.append({
                    'symbol': symbol,
                    'datetime': datetime.now(),
                    'open': price * 0.999,
                    'high': price * 1.002,
                    'low': price * 0.998,
                    'close': price,
                    'price': price,
                    'volume': np.random.randint(10000, 100000),
                    'amount': price * np.random.randint(10000, 100000)
                })
            return pd.DataFrame(data)
        else:
            # Real AkShare integration
            try:
                import akshare as ak
                # Note: AkShare returns all A-share stocks, need to filter
                df = ak.stock_zh_a_spot_em()
                df = df[df['代码'].isin(symbols)]
                # Rename columns to standard names
                df = df.rename(columns={
                    '代码': 'symbol',
                    '最新价': 'price',
                    '最高': 'high',
                    '最低': 'low',
                    '开盘': 'open',
                    '成交量': 'volume',
                    '成交额': 'amount'
                })
                df['datetime'] = datetime.now()
                df['close'] = df['price']
                return df
            except Exception as e:
                logger.error(f"Failed to fetch AkShare data: {e}")
                return pd.DataFrame()
    
    async def _process_symbol(self, symbol: str, data: pd.DataFrame):
        """Process a single symbol and generate signals."""
        if not self.strategy:
            return
        
        # Update strategy data
        try:
            self.strategy.set_data(data)
            signal = self.strategy.get_latest_signal()
            
            if signal and signal.signal_type == SignalType.BUY:
                if signal.confidence >= self.strategy.config.min_confidence:
                    logger.info(f"Signal generated: {signal.symbol} - {signal.reason}")
                    
                    # Callback
                    if self._on_signal_callback:
                        self._on_signal_callback(signal)
                    
                    # Execute
                    await self._execute_signal(signal)
                    
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
    
    async def _execute_signal(self, signal: Signal):
        """Execute a trading signal."""
        symbol = signal.symbol
        price = self._latest_prices.get(symbol, signal.price)
        
        # Check with risk manager
        position_value = self._capital * self.config.position_size_pct
        risk_check = self.risk_manager.check_buy_signal(symbol, position_value)
        
        if not risk_check.is_allowed:
            result = ExecutionResult(
                signal=signal,
                success=False,
                reason=f"Risk rejected: {risk_check.message}"
            )
            self._execution_history.append(result)
            logger.warning(f"Signal rejected by risk manager: {risk_check.message}")
            return
        
        # Calculate quantity
        entry_price = price * (1 + self.config.simulated_slippage_pct)
        quantity = int(position_value / entry_price / 100) * 100
        
        if quantity <= 0:
            result = ExecutionResult(
                signal=signal,
                success=False,
                reason="Insufficient capital for minimum lot size"
            )
            self._execution_history.append(result)
            return
        
        # Simulate execution
        if self.config.mode == EngineMode.SIMULATION:
            # Deduct capital
            commission = quantity * entry_price * self.config.simulated_commission_rate
            cost = quantity * entry_price + commission
            
            if cost > self._capital:
                result = ExecutionResult(
                    signal=signal,
                    success=False,
                    reason="Insufficient capital"
                )
                self._execution_history.append(result)
                return
            
            self._capital -= cost
            
            # Create position
            position = Position(
                symbol=symbol,
                entry_price=entry_price,
                quantity=quantity,
                entry_time=datetime.now(),
                current_price=entry_price
            )
            self._positions[symbol] = position
            self.risk_manager.add_position(position)
            
            result = ExecutionResult(
                signal=signal,
                success=True,
                executed_price=entry_price,
                executed_quantity=quantity,
                reason="Simulated execution"
            )
            self._execution_history.append(result)
            
            logger.info(
                f"SIMULATED BUY: {symbol} @ {entry_price:.2f} x {quantity}"
            )
        else:
            # Live execution would go here
            logger.warning("Live trading not implemented")
            result = ExecutionResult(
                signal=signal,
                success=False,
                reason="Live trading not implemented"
            )
            self._execution_history.append(result)
        
        # Callback
        if self._on_execution_callback:
            self._on_execution_callback(result)
    
    async def _execute_stop_loss(self, symbol: str):
        """Execute stop-loss for a position."""
        if symbol not in self._positions:
            return
        
        pos = self._positions[symbol]
        price = self._latest_prices.get(symbol, pos.current_price)
        
        logger.warning(f"Executing STOP-LOSS for {symbol} @ {price:.2f}")
        
        if self.config.mode == EngineMode.SIMULATION:
            # Return capital
            exit_price = price * (1 - self.config.simulated_slippage_pct)
            sell_value = pos.quantity * exit_price
            commission = sell_value * self.config.simulated_commission_rate
            stamp_tax = sell_value * 0.001  # 印花税
            
            net_return = sell_value - commission - stamp_tax
            self._capital += net_return
            
            # Remove position
            del self._positions[symbol]
            self.risk_manager.remove_position(symbol)
            
            logger.info(f"SIMULATED STOP-LOSS: {symbol} @ {exit_price:.2f}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        return {
            "mode": self.config.mode.value,
            "running": self._running,
            "capital": self._capital,
            "position_count": len(self._positions),
            "positions": {
                symbol: {
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "pnl_pct": pos.pnl_percent,
                    "quantity": pos.quantity
                }
                for symbol, pos in self._positions.items()
            },
            "execution_count": len(self._execution_history),
            "risk_status": self.risk_manager.get_status()
        }
