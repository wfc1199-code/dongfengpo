"""
AI Quant Platform - Backtest Engine
Bar-by-bar simulation engine with parameter sweep and out-of-sample testing.

Features:
- Minute-level backtesting
- Transaction cost modeling (commission, slippage)
- Performance metrics calculation
- Parameter sweep optimization
- Walk-forward validation
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Type
from itertools import product
import pandas as pd
import numpy as np

from ..strategies.base import BaseStrategy, Signal, SignalType, StrategyConfig
from ..risk.manager import RiskManager, RiskConfig, Position, RiskCheckResult

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a completed trade."""
    symbol: str
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    quantity: int
    side: str  # 'long' or 'short'
    pnl: float
    pnl_pct: float
    exit_reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "entry_time": self.entry_time.isoformat(),
            "entry_price": self.entry_price,
            "exit_time": self.exit_time.isoformat(),
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "side": self.side,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "exit_reason": self.exit_reason
        }


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    initial_capital: float = 1_000_000
    commission_rate: float = 0.0003  # 万三 (buy + sell)
    stamp_tax_rate: float = 0.001  # 千分之一 (sell only, A-share)
    slippage_pct: float = 0.001  # 0.1% slippage
    position_size_pct: float = 0.1  # 10% per trade
    max_positions: int = 5
    stop_loss_pct: float = 0.03  # 3%
    take_profit_pct: float = 0.10  # 10%
    
    # Out-of-sample testing
    train_ratio: float = 0.8  # 80% training, 20% testing


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    config: BacktestConfig
    strategy_name: str
    start_date: datetime
    end_date: datetime
    
    # Performance metrics
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    
    # Trade details
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    
    # Parameter info (for sweep)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_return": round(self.total_return, 4),
            "annual_return": round(self.annual_return, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_drawdown": round(self.max_drawdown, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 2),
            "total_trades": self.total_trades,
            "parameters": self.parameters
        }


class BacktestEngine:
    """
    Bar-by-bar backtesting engine.
    
    Simulates strategy execution on historical data with realistic
    transaction costs and risk management.
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        
        # State
        self._capital = self.config.initial_capital
        self._positions: Dict[str, Position] = {}
        self._trades: List[Trade] = []
        self._equity_curve: List[Tuple[datetime, float]] = []
        self._high_watermark = self.config.initial_capital
        self._latest_prices: Dict[str, float] = {}
        
        logger.info(f"BacktestEngine initialized with capital: {self.config.initial_capital:,.0f}")
    
    def _reset(self):
        """Reset engine state for new backtest."""
        self._capital = self.config.initial_capital
        self._positions = {}
        self._trades = []
        self._equity_curve = []
        self._high_watermark = self.config.initial_capital
        self._latest_prices = {}
    
    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str = "BACKTEST"
    ) -> BacktestResult:
        """
        Run backtest on historical data.
        
        Args:
            strategy: Strategy instance to test
            data: DataFrame with OHLCV data
            symbol: Symbol for the backtest
        
        Returns:
            BacktestResult with performance metrics
        """
        self._reset()
        
        # Initialize strategy with data
        data = data.copy()
        if 'symbol' not in data.columns:
            data['symbol'] = symbol
        strategy.set_data(data)
        
        start_date = pd.to_datetime(data['datetime'].iloc[0])
        end_date = pd.to_datetime(data['datetime'].iloc[-1])
        
        logger.info(f"Running backtest: {strategy.name} on {symbol} ({start_date} to {end_date})")
        
        # Bar-by-bar simulation
        for i in range(strategy.config.lookback_days, len(data)):
            row = data.iloc[i]
            current_time = pd.to_datetime(row['datetime'])
            current_price = row['close']
            current_symbol = row['symbol']
            
            # Track latest price
            self._latest_prices[current_symbol] = current_price
            
            # Update positions with current price (ONLY for this symbol)
            self._update_positions(current_price, current_time, current_symbol)
            
            # Check for exit conditions (ONLY for this symbol)
            self._check_exits(current_price, current_time, current_symbol)
            
            # Generate signal
            signal = strategy.generate_signal(i)
            
            # Process buy signals
            if signal and signal.signal_type == SignalType.BUY:
                if signal.confidence >= strategy.config.min_confidence:
                    self._process_buy_signal(signal, current_price, current_time, signal.symbol)
            
            # Record equity (using latest prices for all positions)
            equity = self._calculate_equity()
            self._equity_curve.append((current_time, equity))
            
            # Update high watermark
            if equity > self._high_watermark:
                self._high_watermark = equity
        
        # Close all remaining positions
        if data.shape[0] > 0:
            final_price = data.iloc[-1]['close']
            final_time = pd.to_datetime(data.iloc[-1]['datetime'])
            self._close_all_positions(final_price, final_time, "end_of_backtest")
        
        # Calculate metrics
        result = self._calculate_metrics(strategy.name, start_date, end_date)
        
        logger.info(
            f"Backtest complete: {result.total_trades} trades, "
            f"Return={result.total_return:.2%}, "
            f"Sharpe={result.sharpe_ratio:.2f}"
        )
        
        return result
    
    def _process_buy_signal(
        self,
        signal: Signal,
        current_price: float,
        current_time: datetime,
        symbol: str
    ):
        """Process a buy signal and open position if valid."""
        # Check if already in position
        if symbol in self._positions:
            return
        
        # Check max positions
        if len(self._positions) >= self.config.max_positions:
            return
        
        # Calculate position size
        position_value = self._capital * self.config.position_size_pct
        
        # Apply slippage (buy at higher price)
        entry_price = current_price * (1 + self.config.slippage_pct)
        
        # Calculate quantity
        quantity = int(position_value / entry_price / 100) * 100  # Round to 100 shares
        if quantity <= 0:
            return
        
        # Deduct commission
        commission = quantity * entry_price * self.config.commission_rate
        actual_cost = quantity * entry_price + commission
        
        if actual_cost > self._capital:
            return
        
        # Open position
        self._capital -= actual_cost
        self._positions[symbol] = Position(
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            entry_time=current_time,
            current_price=entry_price
        )
        
        logger.debug(f"Opened position: {symbol} @ {entry_price:.2f} x {quantity}")
    
    def _update_positions(self, current_price: float, current_time: datetime, symbol: str):
        """Update position price for the specific symbol."""
        if symbol in self._positions:
            self._positions[symbol].current_price = current_price
    
    def _check_exits(self, current_price: float, current_time: datetime, symbol: str):
        """Check stop-loss and take-profit conditions for the specific symbol."""
        if symbol not in self._positions:
            return
            
        pos = self._positions[symbol]
        pnl_pct = pos.pnl_percent
        
        # Stop loss
        if pnl_pct <= -self.config.stop_loss_pct:
            self._close_position(symbol, current_price, current_time, "stop_loss")
        
        # Take profit
        elif pnl_pct >= self.config.take_profit_pct:
            self._close_position(symbol, current_price, current_time, "take_profit")
    
    def _close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_time: datetime,
        reason: str
    ):
        """Close a position and record the trade."""
        if symbol not in self._positions:
            return
        
        pos = self._positions.pop(symbol)
        
        # Apply slippage (sell at lower price)
        actual_exit_price = exit_price * (1 - self.config.slippage_pct)
        
        # Calculate costs: commission + stamp tax (A-share: stamp tax on sell only)
        sell_value = pos.quantity * actual_exit_price
        commission = sell_value * self.config.commission_rate
        stamp_tax = sell_value * self.config.stamp_tax_rate  # 印花税
        total_cost = commission + stamp_tax
        
        # Calculate P&L
        gross_pnl = (actual_exit_price - pos.entry_price) * pos.quantity
        net_pnl = gross_pnl - total_cost  # Deduct both commission and stamp tax
        pnl_pct = (actual_exit_price - pos.entry_price) / pos.entry_price
        
        # Return capital
        self._capital += sell_value - total_cost
        
        # Record trade
        trade = Trade(
            symbol=symbol,
            entry_time=pos.entry_time,
            entry_price=pos.entry_price,
            exit_time=exit_time,
            exit_price=actual_exit_price,
            quantity=pos.quantity,
            side="long",
            pnl=net_pnl,
            pnl_pct=pnl_pct,
            exit_reason=reason
        )
        self._trades.append(trade)
        
        logger.debug(f"Closed position: {symbol} @ {actual_exit_price:.2f}, PnL={pnl_pct:.2%}")
    
    def _close_all_positions(self, price: float, time: datetime, reason: str):
        """Close all open positions."""
        symbols = list(self._positions.keys())
        for symbol in symbols:
            self._close_position(symbol, price, time, reason)
    
    def _calculate_equity(self) -> float:
        """Calculate current equity using latest prices for all held positions."""
        position_value = 0
        for symbol, pos in self._positions.items():
            # Use tracked latest price for the symbol
            price = self._latest_prices.get(symbol, pos.entry_price)
            position_value += pos.quantity * price
        return self._capital + position_value
    
    def _calculate_metrics(
        self,
        strategy_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> BacktestResult:
        """Calculate performance metrics."""
        result = BacktestResult(
            config=self.config,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            trades=self._trades,
            equity_curve=self._equity_curve
        )
        
        if not self._trades:
            return result
        
        # Total return
        final_equity = self._equity_curve[-1][1] if self._equity_curve else self.config.initial_capital
        result.total_return = (final_equity - self.config.initial_capital) / self.config.initial_capital
        
        # Annualized return
        days = (end_date - start_date).days
        if days > 0:
            result.annual_return = (1 + result.total_return) ** (365 / days) - 1
        
        # Trade statistics
        result.total_trades = len(self._trades)
        winning_trades = [t for t in self._trades if t.pnl > 0]
        losing_trades = [t for t in self._trades if t.pnl <= 0]
        
        if result.total_trades > 0:
            result.win_rate = len(winning_trades) / result.total_trades
        
        # Profit factor
        total_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 1
        result.profit_factor = total_profit / total_loss if total_loss > 0 else total_profit
        
        # Max drawdown
        if self._equity_curve:
            equity_series = pd.Series([e[1] for e in self._equity_curve])
            running_max = equity_series.expanding().max()
            drawdown = (equity_series - running_max) / running_max
            result.max_drawdown = abs(drawdown.min())
        
        # Sharpe ratio (simplified: using daily returns)
        if len(self._equity_curve) > 1:
            equity_series = pd.Series([e[1] for e in self._equity_curve])
            returns = equity_series.pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                # Assume 240 trading days per year
                result.sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(240)
        
        return result
    
    def run_parameter_sweep(
        self,
        strategy_class: Type[BaseStrategy],
        config_class: Type[StrategyConfig],
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        symbol: str = "BACKTEST",
        use_walk_forward: bool = True,
        train_ratio: float = 0.7
    ) -> List[BacktestResult]:
        """
        Run backtest with multiple parameter combinations.
        
        Args:
            strategy_class: Strategy class to instantiate
            config_class: Config class for the strategy
            data: Historical data
            param_grid: Dict of parameter names to lists of values
            symbol: Symbol for backtesting
            use_walk_forward: If True, use walk-forward validation (out-of-sample) to avoid overfitting
            train_ratio: Ratio of data used for training (only used if use_walk_forward=True)
        
        Returns:
            List of BacktestResult sorted by out-of-sample Sharpe ratio (if walk-forward) or in-sample Sharpe
        """
        results = []
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        
        mode_str = "walk-forward" if use_walk_forward else "in-sample (WARNING: may overfit)"
        logger.info(f"Running parameter sweep: {len(combinations)} combinations ({mode_str})")
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            try:
                # Create config with parameters
                config = config_class(**params)
                strategy = strategy_class(config)
                
                if use_walk_forward:
                    # Use walk-forward validation for out-of-sample performance
                    train_result, test_result = self.run_walk_forward(
                        strategy, data, symbol, train_ratio
                    )
                    # Use test (out-of-sample) result as the primary metric
                    result = test_result
                    result.parameters = params
                    # Store training Sharpe for reference
                    result.parameters['_train_sharpe'] = train_result.sharpe_ratio
                else:
                    # Traditional in-sample approach (warning about overfitting)
                    result = self.run(strategy, data, symbol)
                    result.parameters = params
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Sweep failed for params {params}: {e}")
        
        # Sort by Sharpe ratio (out-of-sample if walk-forward, in-sample otherwise)
        results.sort(key=lambda r: r.sharpe_ratio, reverse=True)
        
        if results:
            best = results[0]
            if use_walk_forward:
                train_sharpe = best.parameters.get('_train_sharpe', 0)
                logger.info(
                    f"Sweep complete. Best OOS Sharpe: {best.sharpe_ratio:.2f} "
                    f"(Train Sharpe: {train_sharpe:.2f})"
                )
            else:
                logger.info(f"Sweep complete. Best Sharpe: {best.sharpe_ratio:.2f}")
        else:
            logger.warning("Parameter sweep completed with no results")
        
        return results
    
    def run_walk_forward(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str = "BACKTEST",
        train_ratio: float = 0.8
    ) -> Tuple[BacktestResult, BacktestResult]:
        """
        Run walk-forward validation (train/test split).
        
        Args:
            strategy: Strategy to test
            data: Historical data
            symbol: Symbol for backtesting
            train_ratio: Ratio for training set
        
        Returns:
            Tuple of (train_result, test_result)
        """
        split_idx = int(len(data) * train_ratio)
        train_data = data.iloc[:split_idx].copy()
        test_data = data.iloc[split_idx:].copy()
        
        logger.info(f"Walk-forward: Train={len(train_data)} bars, Test={len(test_data)} bars")
        
        # Train
        train_result = self.run(strategy, train_data, f"{symbol}_train")
        
        # Test (reinitialize strategy)
        strategy.set_data(test_data)
        test_result = self.run(strategy, test_data, f"{symbol}_test")
        
        logger.info(
            f"Walk-forward results: "
            f"Train Sharpe={train_result.sharpe_ratio:.2f}, "
            f"Test Sharpe={test_result.sharpe_ratio:.2f}"
        )
        
        return train_result, test_result
