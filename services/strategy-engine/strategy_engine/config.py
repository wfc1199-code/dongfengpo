"""Configuration models for strategy engine."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class StrategyConfig(BaseSettings):
    """Configuration for a single strategy plugin."""

    name: str
    module: str
    class_name: str
    enabled: bool = True
    parameters: Dict[str, object] = Field(default_factory=dict)


class StrategyEngineSettings(BaseSettings):
    """Runtime settings for strategy engine."""

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    feature_channel: str = Field("dfp:features", alias="FEATURE_CHANNEL")
    signal_stream: str = Field("dfp:strategy_signals", alias="SIGNAL_STREAM")
    max_stream_length: Optional[int] = Field(None, alias="MAX_STREAM_LENGTH")
    approximate_trim: bool = Field(True, alias="APPROXIMATE_TRIM")
    strategies: List[StrategyConfig] = Field(default_factory=list)

    class Config:
        env_prefix = "STRATEGY_ENGINE_"
        case_sensitive = False


@lru_cache()
def get_settings() -> StrategyEngineSettings:
    settings = StrategyEngineSettings()  # type: ignore[arg-type]

    # Load strategies from JSON config if available
    config_file = os.environ.get(
        "STRATEGY_ENGINE_CONFIG_FILE",
        str(Path(__file__).parent.parent / "strategies_config.json")
    )

    if Path(config_file).exists():
        try:
            with open(config_file, "r") as f:
                strategies_data = json.load(f)
                settings.strategies = [StrategyConfig(**s) for s in strategies_data]
        except Exception as e:
            import logging
            logging.error(f"Failed to load strategies config from {config_file}: {e}")

    return settings
