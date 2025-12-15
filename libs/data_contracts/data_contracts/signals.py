"""Strategy and opportunity signal contracts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class OpportunityState(str, Enum):
    """Lifecycle for aggregated opportunities."""

    NEW = "NEW"
    ACTIVE = "ACTIVE"
    TRACKING = "TRACKING"
    CLOSED = "CLOSED"


class StrategySignal(BaseModel):
    """Normalized strategy output."""

    strategy: str = Field(..., description="策略名称或标识")
    symbol: str = Field(..., description="证券代码")
    signal_type: str = Field(..., description="信号类型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    strength_score: float = Field(..., ge=0.0, description="强度评分")
    reasons: List[str] = Field(default_factory=list, description="触发原因列表")
    triggered_at: datetime = Field(..., description="信号触发时间")
    window: str = Field(..., description="对应的特征窗口标识")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class OpportunitySignal(BaseModel):
    """Aggregated opportunity composed of multiple strategy signals."""

    id: str = Field(..., description="机会唯一标识")
    symbol: str = Field(..., description="证券代码")
    state: OpportunityState = Field(OpportunityState.NEW, description="机会状态")
    created_at: datetime = Field(..., description="首次创建时间")
    updated_at: datetime = Field(..., description="最近更新时间")
    confidence: float = Field(..., ge=0.0, le=1.0, description="综合置信度")
    strength_score: float = Field(..., ge=0.0, description="综合强度评分")
    notes: List[str] = Field(default_factory=list, description="备注信息")
    signals: List[StrategySignal] = Field(default_factory=list, description="关联策略信号")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "sh600000-1709888400",
                "symbol": "sh600000",
                "state": "NEW",
                "created_at": "2024-03-08T09:38:00+08:00",
                "updated_at": "2024-03-08T09:38:05+08:00",
                "confidence": 0.82,
                "strength_score": 76.5,
                "notes": ["策略 rapid-rise 触发"],
                "signals": [
                    {
                        "strategy": "rapid-rise",
                        "symbol": "sh600000",
                        "signal_type": "rapid_rise",
                        "confidence": 0.82,
                        "strength_score": 76.5,
                        "reasons": ["涨幅 2.3%"],
                        "triggered_at": "2024-03-08T09:38:05+08:00",
                        "window": "5s",
                        "metadata": {
                            "price": 12.56,
                            "avg_price": 12.40
                        }
                    }
                ],
            }
        }
    }
