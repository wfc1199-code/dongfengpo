"""Tests for Tencent adapter utilities."""

from __future__ import annotations

from collector_gateway.adapters.tencent import TencentAdapter


def test_parse_response_extracts_tick() -> None:
    adapter = TencentAdapter()

    payload = (
        'v_sh600000="1~浦发银行~600000~10.23~0.12~1.19~12345~456789.0~10.00~9.90~10.50~9.80~0~0~";'
    )

    ticks = adapter._parse_response(payload)  # type: ignore[attr-defined]

    assert len(ticks) == 1
    tick = ticks[0]
    assert tick.symbol == "sh600000"
    assert tick.price == 10.23
    assert tick.volume == 12345
    assert tick.turnover == 456789.0


def test_normalize_symbols_handles_prefixes() -> None:
    adapter = TencentAdapter()
    normalized = adapter._normalize_symbols(["600000", "sz002594", "", "abc"])
    assert normalized == ["sh600000", "sz002594"]
