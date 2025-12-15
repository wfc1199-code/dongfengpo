"""Feature-level data contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FeatureSnapshot(BaseModel):
    """Rolling window statistics calculated from cleaned ticks."""

    symbol: str = Field(..., description="证券代码")
    window: str = Field(..., description="窗口标识，如 5s/1m")
    timestamp: datetime = Field(..., description="窗口对应的最新时间")
    price: float = Field(..., description="窗口内最新成交价")
    change_percent: Optional[float] = Field(None, description="窗口起点到终点的涨跌幅(%)")
    volume_sum: int = Field(..., ge=0, description="窗口内成交量累计")
    avg_price: float = Field(..., ge=0.0, description="窗口内均价")
    max_price: float = Field(..., ge=0.0, description="窗口内最高价")
    min_price: float = Field(..., ge=0.0, description="窗口内最低价")
    turnover_sum: float = Field(..., ge=0.0, description="窗口内成交额累计")
    sample_size: int = Field(..., ge=1, description="窗口内样本数量")

    model_config = {
        "json_schema_extra": {
            "example": {
                "symbol": "sz000001",
                "window": "5s",
                "timestamp": "2024-03-08T09:36:05+08:00",
                "price": 12.5,
                "change_percent": 1.2,
                "volume_sum": 35000,
                "avg_price": 12.42,
                "max_price": 12.6,
                "min_price": 12.3,
                "turnover_sum": 435000.0,
                "sample_size": 15,
            }
        }
    }
