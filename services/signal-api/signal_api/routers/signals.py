"""Routes for strategy signals."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_signal_repository
from ..models import StrategySignalResponse
from ..signal_repository import SignalRepository

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=List[StrategySignalResponse])
async def list_signals(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of signals to return"),
    strategy: Optional[str] = Query(None, description="Filter by strategy name (e.g., 'anomaly_detection')"),
    symbol: Optional[str] = Query(None, description="Filter by stock symbol (e.g., 'sh600000')"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    repository: SignalRepository = Depends(get_signal_repository),
) -> List[StrategySignalResponse]:
    """
    List strategy signals from the data pipeline.

    Returns recent signals with optional filtering by strategy, symbol, signal type, and confidence.
    """
    return await repository.list_signals(
        limit=limit,
        strategy=strategy,
        symbol=symbol,
        signal_type=signal_type,
        min_confidence=min_confidence
    )


@router.get("/stats", response_model=dict)
async def get_signal_stats(
    repository: SignalRepository = Depends(get_signal_repository),
) -> dict:
    """
    Get statistics about recent signals.

    Returns counts by strategy, signal type, and other metrics.
    """
    return await repository.get_signal_stats()


@router.get("/{symbol}", response_model=List[StrategySignalResponse])
async def get_signals_by_symbol(
    symbol: str,
    limit: int = Query(20, ge=1, le=200),
    repository: SignalRepository = Depends(get_signal_repository),
) -> List[StrategySignalResponse]:
    """
    Get all signals for a specific symbol.

    Returns recent signals for the given stock code.
    """
    signals = await repository.list_signals(limit=limit, symbol=symbol)
    if not signals:
        raise HTTPException(status_code=404, detail=f"No signals found for symbol {symbol}")
    return signals
