"""Transformation helpers for cleaning raw ticks."""

from __future__ import annotations

from datetime import datetime
from typing import List

from .models import CleanTick, RawTick


def clean_tick(raw: RawTick, *, cleaned_at: datetime | None = None) -> CleanTick:
    """Normalize and repair a raw tick record."""

    cleaned_at = cleaned_at or datetime.utcnow()
    flags: List[str] = []

    price = max(raw.price, 0.0)
    if raw.price < 0:
        flags.append("negative_price")

    volume = max(raw.volume, 0)
    if raw.volume < 0:
        flags.append("negative_volume")

    turnover = raw.turnover
    if turnover <= 0 and price > 0 and volume > 0:
        turnover = price * volume
        flags.append("turnover_reconstructed")
    elif turnover < 0:
        turnover = 0.0
        flags.append("negative_turnover")

    bid_price = _sanitize_optional(raw.bid_price, flags, "bid_price")
    ask_price = _sanitize_optional(raw.ask_price, flags, "ask_price")

    bid_volume = _sanitize_optional_int(raw.bid_volume, flags, "bid_volume")
    ask_volume = _sanitize_optional_int(raw.ask_volume, flags, "ask_volume")

    return CleanTick(
        symbol=raw.symbol,
        price=price,
        volume=volume,
        turnover=turnover,
        bid_price=bid_price,
        bid_volume=bid_volume,
        ask_price=ask_price,
        ask_volume=ask_volume,
        source=raw.source,
        timestamp=raw.timestamp,
        ingested_at=raw.ingested_at,
        cleaned_at=cleaned_at,
        quality_flags=flags,
        raw=raw.raw,
    )


def _sanitize_optional(value: float | None, flags: List[str], name: str) -> float | None:
    if value is None:
        return None
    if value < 0:
        flags.append(f"{name}_negative")
        return None
    return value


def _sanitize_optional_int(value: int | None, flags: List[str], name: str) -> int | None:
    if value is None:
        return None
    if value < 0:
        flags.append(f"{name}_negative")
        return None
    return value
