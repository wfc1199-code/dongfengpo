"""Configuration for feature pipeline service."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class WindowConfig(BaseSettings):
    """Configuration for a rolling window calculation."""

    name: str
    window_size: int = Field(5, ge=1)
    window_unit: str = Field("seconds")  # seconds | minutes


class FeaturePipelineSettings(BaseSettings):
    """Runtime settings."""

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    input_stream: str = Field("dfp:clean_ticks", alias="INPUT_STREAM")
    consumer_group: str = Field("feature-pipeline", alias="CONSUMER_GROUP")
    consumer_name: str = Field("feature-worker-1", alias="CONSUMER_NAME")
    read_count: int = Field(500, ge=1, alias="READ_COUNT")
    block_ms: int = Field(1000, ge=1, alias="BLOCK_MS")
    publish_channel: str = Field("dfp:features", alias="PUBLISH_CHANNEL")

    windows: List[WindowConfig] = Field(default_factory=lambda: [WindowConfig(name="5s", window_size=5, window_unit="seconds")])

    class Config:
        env_prefix = "FEATURE_PIPELINE_"
        case_sensitive = False


@lru_cache()
def get_settings() -> FeaturePipelineSettings:
    return FeaturePipelineSettings()  # type: ignore[arg-type]
