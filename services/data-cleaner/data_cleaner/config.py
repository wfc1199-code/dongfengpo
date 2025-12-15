"""Configuration models for the data cleaner service."""

from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class CleanerSettings(BaseSettings):
    """Runtime configuration for the cleaner service."""

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    input_stream: str = Field("dfp:raw_ticks", alias="INPUT_STREAM")
    output_stream: str = Field("dfp:clean_ticks", alias="OUTPUT_STREAM")
    consumer_group: str = Field("data-cleaner", alias="CONSUMER_GROUP")
    consumer_name: str = Field("worker-1", alias="CONSUMER_NAME")
    read_count: int = Field(200, ge=1, alias="READ_COUNT")
    block_ms: int = Field(1000, ge=1, alias="BLOCK_MS")
    max_output_len: int | None = Field(None, alias="MAX_OUTPUT_LEN")
    approximate_trim: bool = Field(True, alias="APPROXIMATE_TRIM")

    class Config:
        env_prefix = "CLEANER_"
        case_sensitive = False


@lru_cache()
def get_settings() -> CleanerSettings:
    """Return cached settings instance."""

    return CleanerSettings()  # type: ignore[arg-type]
