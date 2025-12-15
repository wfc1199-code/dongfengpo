"""Tick-level data contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TickRecord(BaseModel):
    """Normalized tick data point emitted by the collector."""

    source: str = Field(..., description="数据来源适配器标识")
    symbol: str = Field(..., description="证券代码，含市场标识")
    price: float = Field(..., description="最新成交价")
    volume: int = Field(..., description="成交量（手）")
    turnover: float = Field(..., description="成交额")
    bid_price: Optional[float] = Field(None, description="买一价")
    bid_volume: Optional[int] = Field(None, description="买一量")
    ask_price: Optional[float] = Field(None, description="卖一价")
    ask_volume: Optional[int] = Field(None, description="卖一量")
    timestamp: datetime = Field(..., description="行情时间")
    ingested_at: datetime = Field(..., description="数据写入时间")
    raw: Dict[str, Any] = Field(default_factory=dict, description="原始字段备份")

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("symbol cannot be empty")
        return normalized.lower()

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "tencent",
                "symbol": "sh600000",
                "price": 12.34,
                "volume": 1200,
                "turnover": 14808.0,
                "bid_price": 12.33,
                "bid_volume": 800,
                "ask_price": 12.34,
                "ask_volume": 600,
                "timestamp": "2024-03-08T09:35:05.000+08:00",
                "ingested_at": "2024-03-08T09:35:05.100+08:00",
                "raw": {"v": "stub"},
            }
        }
    }


class CleanedTick(TickRecord):
    """Tick record after cleaner normalization."""

    price: float = Field(..., ge=0.0, description="最新成交价")
    volume: int = Field(..., ge=0, description="成交量（手）")
    turnover: float = Field(..., ge=0.0, description="成交额")
    bid_price: Optional[float] = Field(None, ge=0.0, description="买一价")
    bid_volume: Optional[int] = Field(None, ge=0, description="买一量")
    ask_price: Optional[float] = Field(None, ge=0.0, description="卖一价")
    ask_volume: Optional[int] = Field(None, ge=0, description="卖一量")
    cleaned_at: datetime = Field(..., description="清洗完成时间")
    quality_flags: List[str] = Field(default_factory=list, description="质量标记")
