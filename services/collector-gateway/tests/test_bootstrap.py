"""Tests for adapter bootstrap helpers."""

from __future__ import annotations

from collector_gateway.adapters.tencent import TencentAdapter
from collector_gateway.bootstrap import build_adapters
from collector_gateway.config import CollectorSettings


def test_build_adapters_returns_default_when_none_configured() -> None:
    settings = CollectorSettings()

    adapters = build_adapters(settings)

    assert len(adapters) == 1
    assert isinstance(adapters[0], TencentAdapter)


def test_build_adapters_uses_configuration_values() -> None:
    settings = CollectorSettings(
        data_sources=[
            {
                "name": "tencent",
                "base_url": "http://example.com/q=",
                "poll_interval_seconds": 2.5,
                "timeout_seconds": 3.5,
                "max_batch_size": 50,
            }
        ]
    )

    adapters = build_adapters(settings)

    assert len(adapters) == 1
    adapter = adapters[0]
    assert isinstance(adapter, TencentAdapter)
    assert adapter.config.base_url == "http://example.com/q="
    assert adapter.config.poll_interval == 2.5
    assert adapter.config.request_timeout == 3.5
    assert adapter.config.max_symbols_per_request == 50
