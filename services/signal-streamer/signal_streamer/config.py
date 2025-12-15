"""Configuration for WebSocket signal streamer."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class SignalStreamerSettings(BaseSettings):
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    opportunity_stream: str = Field("dfp:opportunities", alias="OPPORTUNITY_STREAM")
    channel_name: str = Field("dfp:opportunities:ws", alias="CHANNEL_NAME")
    risk_channel: str | None = Field("dfp:risk_alerts", alias="RISK_CHANNEL")

    class Config:
        env_prefix = "SIGNAL_STREAMER_"
        case_sensitive = False


@lru_cache()
def get_settings() -> SignalStreamerSettings:
    return SignalStreamerSettings()  # type: ignore[arg-type]
