"""Configuration for Signal API service."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class SignalApiSettings(BaseSettings):
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    opportunity_stream: str = Field("dfp:opportunities", alias="OPPORTUNITY_STREAM")
    max_records: int = Field(200, ge=1, alias="MAX_RECORDS")

    class Config:
        env_prefix = "SIGNAL_API_"
        case_sensitive = False


@lru_cache()
def get_settings() -> SignalApiSettings:
    return SignalApiSettings()  # type: ignore[arg-type]
