"""Simple backtest engine placeholder implementation."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import List

import pandas as pd

from .models import BacktestMetrics, BacktestRequest, BacktestResult, TradeRecord


@dataclass
class PriceSeries:
    timestamps: List[pd.Timestamp]
    prices: List[float]


class BacktestEngine:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def run(self, request: BacktestRequest) -> BacktestResult:
        series = self._load_price_series(request)
        metrics, trades = self._simulate_strategy(request, series)
        return BacktestResult(request=request, metrics=metrics, trades=trades)

    def _load_price_series(self, request: BacktestRequest) -> PriceSeries:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.data_dir / f"{request.symbol}.parquet"
        if file_path.exists():
            frame = pd.read_parquet(file_path)
            frame = frame.set_index("timestamp")
            mask = (frame.index >= pd.Timestamp(request.start_date)) & (frame.index <= pd.Timestamp(request.end_date) + timedelta(days=1))
            frame = frame.loc[mask]
            if not frame.empty:
                return PriceSeries(timestamps=list(frame.index), prices=list(frame["close"]))

        # fallback: generate synthetic walk
        dates = pd.date_range(request.start_date, request.end_date, freq="1D")
        price = 100.0
        prices: List[float] = []
        for _ in dates:
            price += random.uniform(-1.5, 1.8)
            prices.append(max(price, 1.0))
        return PriceSeries(timestamps=list(dates), prices=prices)

    def _simulate_strategy(self, request: BacktestRequest, series: PriceSeries) -> tuple[BacktestMetrics, List[TradeRecord]]:
        trades: List[TradeRecord] = []
        capital = request.initial_capital
        position = 0
        entry_price = 0.0

        for timestamp, price in zip(series.timestamps, series.prices):
            if position == 0 and price < sum(series.prices) / len(series.prices):
                quantity = int(capital / price * 0.1)
                if quantity > 0:
                    position += quantity
                    capital -= quantity * price
                    entry_price = price
                    trades.append(
                        TradeRecord(
                            timestamp=str(timestamp),
                            action="BUY",
                            price=price,
                            quantity=quantity,
                            pnl=0.0,
                        )
                    )
            elif position > 0 and price > entry_price * 1.03:
                capital += position * price
                pnl = (price - entry_price) * position
                trades.append(
                    TradeRecord(
                        timestamp=str(timestamp),
                        action="SELL",
                        price=price,
                        quantity=position,
                        pnl=pnl,
                    )
                )
                position = 0

        portfolio_value = capital + position * series.prices[-1]
        total_return = (portfolio_value - request.initial_capital) / request.initial_capital
        annualized = total_return * 252 / max(len(series.prices), 1)
        max_drawdown = min(-0.05, -total_return / 2)
        sharpe = total_return / 0.1 if total_return != 0 else 0.0
        win_trades = [trade for trade in trades if trade.pnl > 0]
        metrics = BacktestMetrics(
            total_return=round(total_return, 4),
            annualized_return=round(annualized, 4),
            max_drawdown=round(max_drawdown, 4),
            sharpe_ratio=round(sharpe, 4),
            win_rate=round(len(win_trades) / len(trades), 4) if trades else 0.0,
            trades=len(trades),
        )

        return metrics, trades
