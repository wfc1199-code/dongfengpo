"""Model validation tests for data cleaner."""

from __future__ import annotations

from datetime import datetime

import pytest

from data_cleaner.models import RawTick


def test_symbol_normalization():
    tick = RawTick(
        source="tencent",
        symbol=" SH600000 ",
        price=1.0,
        volume=1,
        turnover=1.0,
        timestamp=datetime.utcnow(),
        ingested_at=datetime.utcnow(),
    )
    assert tick.symbol == "sh600000"


def test_symbol_required():
    with pytest.raises(ValueError):
        RawTick(
            source="tencent",
            symbol=" ",
            price=1.0,
            volume=1,
            turnover=1.0,
            timestamp=datetime.utcnow(),
            ingested_at=datetime.utcnow(),
        )
