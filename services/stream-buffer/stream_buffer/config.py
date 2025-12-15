"""Configuration models for stream buffer service."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class TargetStreamConfig(BaseSettings):
    """Configuration for a replication target."""

    name: str
    max_length: Optional[int] = Field(default=None, ge=1)
    approximate: bool = True


class StreamPipelineConfig(BaseSettings):
    """Represents one replication pipeline from a source stream."""

    name: str
    source_stream: str
    start_from: str = Field(default="$", description="Initial ID to start reading from")
    block_ms: int = Field(default=1000, ge=1)
    batch_size: int = Field(default=200, ge=1)
    trim_source_to: Optional[int] = Field(default=None, ge=1)
    targets: List[TargetStreamConfig] = Field(default_factory=list)


class BufferSettings(BaseSettings):
    """Root settings for stream buffer service."""

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    pipelines: List[StreamPipelineConfig] = Field(default_factory=list)

    class Config:
        env_prefix = "BUFFER_"
        case_sensitive = False


@lru_cache()
def get_settings() -> BufferSettings:
    """Return cached settings instance."""

    return BufferSettings()  # type: ignore[arg-type]
