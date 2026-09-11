"""Analyze a Zstandard-compressed newline-delimited JSON data file."""

import argparse
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import zstandard as zstd


def value_type(value: Any) -> str:
    """Return a readable type name for a JSON value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def analyze(path: Path, sample_count: int) -> None:
    columns: set[str] = set()
    type_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    present_counts: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []
    record_count = 0
    invalid_lines = 0

    with path.open("rb") as compressed:
        with zstd.ZstdDecompressor().stream_reader(compressed) as decompressed:
            text_stream = io.TextIOWrapper(decompressed, encoding="utf-8")
            for line_number, line in enumerate(text_stream, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    invalid_lines += 1
                    continue

                if not isinstance(record, dict):
                    invalid_lines += 1
                    continue

                record_count += 1
                if len(samples) < sample_count:
                    samples.append(record)

                for name, value in record.items():
                    columns.add(name)
                    present_counts[name] += 1
                    type_counts[name][value_type(value)] += 1

    print(f"File: {path}")
    print(f"Records: {record_count:,}")
    print(f"Columns: {len(columns)}")
    if invalid_lines:
        print(f"Invalid/non-object lines skipped: {invalid_lines:,}")

    print("\nColumn details:")
    for name in sorted(columns):
        types = ", ".join(
            f"{kind}={count:,}" for kind, count in type_counts[name].most_common()
        )
        missing = record_count - present_counts[name]
        print(f"- {name}: present={present_counts[name]:,}, missing={missing:,}, types={types}")

    print("\nSample records:")
    for index, record in enumerate(samples, start=1):
        print(f"\n[{index}]")
        print(json.dumps(record, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="Zstandard-compressed NDJSON file")
    parser.add_argument(
        "--samples",
        type=int,
        default=3,
        help="number of complete records to display (default: 3)",
    )
    args = parser.parse_args()
    if args.samples < 0:
        parser.error("--samples must be zero or greater")
    analyze(args.file, args.samples)


if __name__ == "__main__":
    main()