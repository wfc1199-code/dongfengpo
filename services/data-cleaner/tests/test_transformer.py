"""Tests for data cleaner transformer."""

from __future__ import annotations

from datetime import datetime

from data_cleaner.models import RawTick
from data_cleaner.transformer import clean_tick


def build_raw(**kwargs):
    base = {
        "source": "tencent",
        "symbol": "sh600000",
        "price": 10.0,
        "volume": 1000,
        "turnover": 10000.0,
        "timestamp": datetime.utcnow(),
        "ingested_at": datetime.utcnow(),
    }
    base.update(kwargs)
    return RawTick(**base)


def test_clean_tick_repairs_negative_values():
    raw = build_raw(price=-1.0, volume=-5, turnover=-10.0)
    cleaned = clean_tick(raw, cleaned_at=datetime.utcnow())

    assert cleaned.price == 0.0
    assert cleaned.volume == 0
    assert cleaned.turnover == 0.0
    assert set(cleaned.quality_flags) >= {
        "negative_price",
        "negative_volume",
        "negative_turnover",
    }


def test_clean_tick_reconstructs_turnover():
    raw = build_raw(turnover=0.0)
    cleaned = clean_tick(raw)

    assert cleaned.turnover == raw.price * raw.volume
    assert "turnover_reconstructed" in cleaned.quality_flags
