"""Data models for signal API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Opportunity(BaseModel):
    """Aggregated opportunity signal."""
    id: str
    symbol: str
    state: str
    created_at: datetime
    updated_at: datetime
    confidence: float
    strength_score: float
    notes: List[str] = Field(default_factory=list)


class StrategySignalResponse(BaseModel):
    """Strategy signal from strategy-engine."""
    strategy: str = Field(..., description="Strategy name (e.g., 'anomaly_detection', 'limit_up_prediction')")
    symbol: str = Field(..., description="Stock symbol (e.g., 'sh600000')")
    signal_type: str = Field(..., description="Signal type (e.g., 'volume_surge', 'limit_up_potential')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    strength_score: float = Field(..., ge=0.0, description="Strength score")
    reasons: List[str] = Field(default_factory=list, description="List of trigger reasons")
    triggered_at: datetime = Field(..., description="When the signal was generated")
    window: str = Field(..., description="Time window (e.g., '5s', '1m')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "strategy": "anomaly_detection",
                "symbol": "sh600000",
                "signal_type": "volume_surge",
                "confidence": 1.0,
                "strength_score": 100.0,
                "reasons": ["放量异动: 量比3797.6倍"],
                "triggered_at": "2025-10-01T12:37:24.768525",
                "window": "5s",
                "metadata": {
                    "volume": 4519180,
                    "volume_ratio": 3797.63
                }
            }
        }
