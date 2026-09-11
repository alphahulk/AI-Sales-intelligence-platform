"""Write normalized observations to Parquet."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def write_parquet(rows: Iterable[dict[str, Any]], output: Path, batch_size: int = 10_000) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    count = 0
    batch: list[dict[str, Any]] = []
    try:
        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                table = pa.Table.from_pylist(batch)
                writer = writer or pq.ParquetWriter(output, table.schema, compression="zstd")
                writer.write_table(table)
                count += len(batch)
                batch.clear()
        if batch:
            table = pa.Table.from_pylist(batch)
            writer = writer or pq.ParquetWriter(output, table.schema, compression="zstd")
            writer.write_table(table)
            count += len(batch)
    finally:
        if writer:
            writer.close()
    return count