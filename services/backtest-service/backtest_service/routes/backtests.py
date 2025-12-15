"""Backtest routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_engine
from ..engine import BacktestEngine
from ..models import BacktestRequest, BacktestResult

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest, engine: BacktestEngine = Depends(get_engine)) -> BacktestResult:
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="start_date must be earlier than end_date")
    result = engine.run(request)
    return result
