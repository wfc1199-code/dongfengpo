"""Configuration for backtest service."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class BacktestSettings(BaseSettings):
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    data_lake_dir: Path = Field(Path("data-lake"), alias="DATA_LAKE_DIR")
    results_dir: Path = Field(Path("backtest-results"), alias="RESULTS_DIR")

    class Config:
        env_prefix = "BACKTEST_"
        case_sensitive = False


@lru_cache()
def get_settings() -> BacktestSettings:
    return BacktestSettings()  # type: ignore[arg-type]
