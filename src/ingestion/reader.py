"""Read Zstandard-compressed NDJSON without loading it into memory."""

import io
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import zstandard as zstd


def read_records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("rb") as compressed:
        with zstd.ZstdDecompressor().stream_reader(compressed) as decompressed:
            text_stream = io.TextIOWrapper(decompressed, encoding="utf-8")
            for line in text_stream:
                if not line.strip():
                    continue
                record = json.loads(line)
                if isinstance(record, dict):
                    yield record