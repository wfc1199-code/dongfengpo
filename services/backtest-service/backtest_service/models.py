"""Data models for backtest service."""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyParameters(BaseModel):
    name: str
    config: Dict[str, float | int | str] = Field(default_factory=dict)


class BacktestRequest(BaseModel):
    symbol: str
    start_date: date
    end_date: date
    strategy: StrategyParameters
    initial_capital: float = Field(100000.0, gt=0)


class TradeRecord(BaseModel):
    timestamp: str
    action: str
    price: float
    quantity: int
    pnl: float


class BacktestMetrics(BaseModel):
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    trades: int


class BacktestResult(BaseModel):
    request: BacktestRequest
    metrics: BacktestMetrics
    trades: List[TradeRecord] = Field(default_factory=list)
    notes: Optional[str] = None
