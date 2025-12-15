"""Tests for stream buffer service internals."""

from __future__ import annotations

from typing import Dict, List

import pytest

from stream_buffer.config import BufferSettings, StreamPipelineConfig, TargetStreamConfig
from stream_buffer.service import PipelineMetrics, StreamBufferService


class DummyRedis:
    def __init__(self) -> None:
        self.add_calls: List[Dict[str, object]] = []

    async def xadd(self, name: str, fields: Dict[str, str], **kwargs) -> None:
        self.add_calls.append({"name": name, "fields": dict(fields), "kwargs": kwargs})

    async def xread(self, *args, **kwargs):  # pragma: no cover - not used in unit tests
        return []

    async def xtrim(self, *args, **kwargs):  # pragma: no cover - not used in unit tests
        return 0


@pytest.mark.asyncio
async def test_handle_entries_updates_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = BufferSettings(pipelines=[])
    service = StreamBufferService(settings=settings, redis_client=DummyRedis())

    pipeline = StreamPipelineConfig(
        name="raw",
        source_stream="dfp:raw_ticks",
        targets=[
            TargetStreamConfig(name="dfp:raw_ticks:backup"),
            TargetStreamConfig(name="dfp:raw_ticks:mirror"),
        ],
    )
    metrics = PipelineMetrics(name="raw", last_id="$")

    async def fake_replicate(targets, payload):  # noqa: ANN001
        pass

    monkeypatch.setattr(service, "_replicate_to_targets", fake_replicate)

    entries = [
        ("1-0", {"payload": "foo"}),
        ("1-1", {"payload": "bar"}),
    ]

    await service._handle_entries(pipeline, entries, metrics)

    assert metrics.processed_messages == 2
    assert metrics.replicated_messages == len(pipeline.targets) * len(entries)
    assert metrics.last_processed_at is not None


@pytest.mark.asyncio
async def test_replicate_to_targets_respects_max_length() -> None:
    redis = DummyRedis()
    settings = BufferSettings(pipelines=[])
    service = StreamBufferService(settings=settings, redis_client=redis)

    targets = [
        TargetStreamConfig(name="dfp:raw_ticks", max_length=10, approximate=True),
        TargetStreamConfig(name="dfp:raw_ticks:archive", max_length=None),
    ]

    await service._replicate_to_targets(targets, {"payload": "data"})

    assert len(redis.add_calls) == 2
    assert redis.add_calls[0]["kwargs"]["maxlen"] == 10
    assert redis.add_calls[0]["kwargs"]["approximate"] is True
    assert redis.add_calls[1]["kwargs"] == {}
