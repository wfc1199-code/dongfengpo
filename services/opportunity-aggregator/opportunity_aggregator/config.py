"""Configuration for opportunity aggregator."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class AggregatorSettings(BaseSettings):
    """Runtime settings."""

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    signal_stream: str = Field("dfp:strategy_signals", alias="SIGNAL_STREAM")
    consumer_group: str = Field("opportunity-aggregator", alias="CONSUMER_GROUP")
    consumer_name: str = Field("aggregator-1", alias="CONSUMER_NAME")
    read_count: int = Field(200, ge=1, alias="READ_COUNT")
    block_ms: int = Field(1000, ge=1, alias="BLOCK_MS")
    opportunity_stream: str = Field("dfp:opportunities", alias="OPPORTUNITY_STREAM")
    opportunity_channel: str | None = Field("dfp:opportunities:ws", alias="OPPORTUNITY_CHANNEL")
    max_stream_length: int | None = Field(None, alias="MAX_STREAM_LENGTH")
    approximate_trim: bool = Field(True, alias="APPROXIMATE_TRIM")
    tracking_expiration_seconds: int = Field(600, ge=1, alias="TRACKING_EXPIRATION_SECONDS")

    class Config:
        env_prefix = "OPPORTUNITY_AGG_"
        case_sensitive = False


@lru_cache()
def get_settings() -> AggregatorSettings:
    return AggregatorSettings()  # type: ignore[arg-type]
