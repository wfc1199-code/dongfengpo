"""Configuration models for the collector gateway service."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class DataSourceConfig(BaseSettings):
    """Generic configuration for a data source adapter."""

    name: str
    enabled: bool = True
    base_url: Optional[HttpUrl] = None
    api_key: Optional[str] = None
    rate_limit_per_minute: int = Field(600, ge=1)
    timeout_seconds: float = Field(5.0, ge=0.1)
    retry_attempts: int = Field(3, ge=0)
    poll_interval_seconds: float = Field(1.0, ge=0.1)
    max_batch_size: int = Field(200, ge=1)


class CollectorSettings(BaseSettings):
    """Application level settings."""

    environment: str = Field("development", alias="ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    stream_name: str = Field("dfp:raw_ticks", alias="STREAM_NAME")
    batch_size: int = Field(100, ge=1)
    flush_interval_seconds: float = Field(0.5, ge=0.01)
    data_sources: List[DataSourceConfig] = Field(default_factory=list)

    class Config:
        env_prefix = "COLLECTOR_"
        case_sensitive = False


@lru_cache()
def get_settings() -> CollectorSettings:
    """Return cached settings instance."""

    return CollectorSettings()  # type: ignore[arg-type]
