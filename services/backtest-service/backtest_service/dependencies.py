"""Dependency providers."""

from __future__ import annotations

from functools import lru_cache

from .config import BacktestSettings, get_settings
from .engine import BacktestEngine


@lru_cache()
def get_engine() -> BacktestEngine:
    settings = get_settings()
    return BacktestEngine(data_dir=settings.data_lake_dir)
