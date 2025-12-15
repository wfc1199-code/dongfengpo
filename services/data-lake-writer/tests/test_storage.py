"""Tests for data lake storage layer."""

from __future__ import annotations

from datetime import datetime
from importlib.util import find_spec
from pathlib import Path

import pytest

from data_lake_writer.models import CleanTickRecord
from data_lake_writer.storage import DataLakeStorage


HAS_PARQUET = find_spec("pyarrow") is not None


def _record() -> CleanTickRecord:
    return CleanTickRecord(
        symbol="sh600000",
        price=10.0,
        volume=1000,
        turnover=10000.0,
        source="tencent",
        timestamp=datetime.utcnow(),
        ingested_at=datetime.utcnow(),
        cleaned_at=datetime.utcnow(),
    )


@pytest.mark.skipif(not HAS_PARQUET, reason="pyarrow not installed")
def test_write_batch_parquet(tmp_path: Path) -> None:
    storage = DataLakeStorage(output_dir=tmp_path, file_format="parquet")
    path = storage.write_batch([_record()], shard="20240101T000000")

    assert path.suffix == ".parquet"
    assert path.exists()


def test_write_batch_csv(tmp_path: Path) -> None:
    storage = DataLakeStorage(output_dir=tmp_path, file_format="csv")
    path = storage.write_batch([_record()], shard="20240101T000001")

    assert path.suffix == ".csv"
    assert path.exists()
