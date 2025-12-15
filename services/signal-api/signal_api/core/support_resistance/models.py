from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class SRType(str, Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"
    PIVOT = "pivot"
    TARGET = "target"

class SRRating(str, Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"

class SRSource(str, Enum):
    FIXED = "fixed"      # 静态规则 (昨收/今开)
    DYNAMIC = "dynamic"  # 动态统计
    TDX = "tdx"          # TDX 算法
    LOCAL = "local"      # 本地计算

class SRLevel(BaseModel):
    price: float
    type: SRType
    strength: float = Field(..., ge=0, le=100, description="Strength score 0-100")
    rating: SRRating
    source: List[SRSource]
    visual_style: Dict[str, Any] = Field(default_factory=dict, description="Frontend visual props like color, dash style")
    description: Optional[str] = None

    class Config:
        use_enum_values = True

class SRAnalysis(BaseModel):
    summary: str
    dominant_trend: str
    closest_support: Optional[float] = None
    closest_resistance: Optional[float] = None
    price_position: str  # e.g. "Above Support", "Testing Resistance"

class SRRequestPayload(BaseModel):
    symbol: str
    prices: List[float]
    highs: Optional[List[float]] = None
    lows: Optional[List[float]] = None
    opens: Optional[List[float]] = None
    volumes: Optional[List[float]] = None
    timestamps: Optional[List[int]] = None # Unix timestamps
    period: str = "1m"
    # Current day data for static rules
    prev_close: Optional[float] = None
    today_open: Optional[float] = None
    today_high: Optional[float] = None
    today_low: Optional[float] = None

class SRResponse(BaseModel):
    success: bool
    levels: List[SRLevel]
    analysis: Optional[SRAnalysis] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
