"""Configuration for the data lake writer service."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class LakeWriterSettings(BaseSettings):
    """Runtime settings."""

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    input_stream: str = Field("dfp:clean_ticks", alias="INPUT_STREAM")
    consumer_group: str = Field("data-lake-writer", alias="CONSUMER_GROUP")
    consumer_name: str = Field("writer-1", alias="CONSUMER_NAME")
    read_count: int = Field(500, ge=1, alias="READ_COUNT")
    block_ms: int = Field(2000, ge=1, alias="BLOCK_MS")

    output_dir: Path = Field(Path("data-lake"), alias="OUTPUT_DIR")
    file_format: Literal["parquet", "csv"] = Field("parquet", alias="FILE_FORMAT")
    flush_interval_seconds: int = Field(60, ge=1, alias="FLUSH_INTERVAL_SECONDS")
    max_buffer_size: int = Field(1000, ge=1, alias="MAX_BUFFER_SIZE")

    class Config:
        env_prefix = "LAKE_WRITER_"
        case_sensitive = False


@lru_cache()
def get_settings() -> LakeWriterSettings:
    return LakeWriterSettings()  # type: ignore[arg-type]
