"""Tests for data lake writer service internals."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List

import pytest

from data_lake_writer.config import LakeWriterSettings
from data_lake_writer.models import CleanTickRecord
from data_lake_writer.service import DataLakeWriterService


class DummyRedis:
    def __init__(self) -> None:
        self.acked: List[str] = []

    async def xgroup_create(self, **kwargs):  # noqa: D401
        raise Exception("BUSYGROUP")

    async def xreadgroup(self, **kwargs):  # pragma: no cover - not used here
        return []

    async def xack(self, stream, group, message_id):
        self.acked.append(message_id)

    async def close(self):  # pragma: no cover
        pass


class DummyStorage:
    def __init__(self) -> None:
        self.written_batches: List[int] = []

    def write_batch(self, records, shard):  # noqa: ANN001
        self.written_batches.append(len(list(records)))
        return shard


@pytest.mark.asyncio
async def test_flush_triggered_by_buffer(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = LakeWriterSettings(max_buffer_size=2)
    service = DataLakeWriterService(settings=settings, redis_client=DummyRedis())

    storage = DummyStorage()
    monkeypatch.setattr(service, "storage", storage)
    async def fake_ack(message_id):  # noqa: ANN001
        return None

    monkeypatch.setattr(service, "_ack", fake_ack)
    service._flush_state.buffer = [
        CleanTickRecord(
            symbol="sh600000",
            price=10.0,
            volume=100,
            turnover=1000.0,
            source="tencent",
            timestamp=datetime.utcnow(),
            ingested_at=datetime.utcnow(),
            cleaned_at=datetime.utcnow(),
        ),
        CleanTickRecord(
            symbol="sh600001",
            price=11.0,
            volume=200,
            turnover=2200.0,
            source="tencent",
            timestamp=datetime.utcnow(),
            ingested_at=datetime.utcnow(),
            cleaned_at=datetime.utcnow(),
        ),
    ]

    await service._flush(force=True)

    assert storage.written_batches == [2]
