"""Configuration for risk guard service."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class RiskGuardSettings(BaseSettings):
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    opportunity_stream: str = Field("dfp:opportunities", alias="OPPORTUNITY_STREAM")
    risk_channel: str = Field("dfp:risk_alerts", alias="RISK_CHANNEL")
    volatility_threshold: float = Field(5.0, alias="VOLATILITY_THRESHOLD")
    drawdown_threshold: float = Field(8.0, alias="DRAWDOWN_THRESHOLD")

    class Config:
        env_prefix = "RISK_GUARD_"
        case_sensitive = False


@lru_cache()
def get_settings() -> RiskGuardSettings:
    return RiskGuardSettings()  # type: ignore[arg-type]
