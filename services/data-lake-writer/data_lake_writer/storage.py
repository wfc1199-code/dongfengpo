"""Storage backend implementations for data lake writer."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Literal

import pandas as pd

from .models import CleanTickRecord


class DataLakeStorage:
    """Persist batches of clean ticks to disk."""

    def __init__(self, output_dir: Path, file_format: Literal["parquet", "csv"] = "parquet") -> None:
        self.output_dir = output_dir
        self.file_format = file_format
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_batch(self, records: Iterable[CleanTickRecord], shard: str) -> Path:
        frame = pd.DataFrame([record.model_dump() for record in records])
        if frame.empty:
            raise ValueError("Cannot write empty dataset")

        output_path = self._build_path(shard)

        if self.file_format == "parquet":
            frame.to_parquet(output_path, index=False)
        else:
            frame.to_csv(output_path, index=False)

        return output_path

    def _build_path(self, shard: str) -> Path:
        suffix = "parquet" if self.file_format == "parquet" else "csv"
        filename = f"ticks_{shard}.{suffix}"
        return self.output_dir / filename
