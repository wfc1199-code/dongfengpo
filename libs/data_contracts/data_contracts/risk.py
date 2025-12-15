"""Risk alert contracts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAlert(BaseModel):
    """Risk notifications connected to opportunities or symbols."""

    symbol: str = Field(..., description="证券代码")
    risk_type: str = Field(..., description="风险类型标识")
    severity: RiskSeverity = Field(..., description="风险等级")
    message: str = Field(..., description="风险说明")
    triggered_at: datetime = Field(..., description="触发时间")
    opportunity_id: str = Field(..., description="关联机会 ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加信息")

