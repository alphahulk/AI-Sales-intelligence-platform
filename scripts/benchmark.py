"""Benchmark streaming ingestion and report elapsed time and throughput."""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.reader import read_records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    records = sum(1 for _ in read_records(args.input))
    elapsed = time.perf_counter() - started
    print(f"Records: {records:,}")
    print(f"Elapsed: {elapsed:.3f} seconds")
    print(f"Records/sec: {records / elapsed:,.1f}" if elapsed else "Records/sec: n/a")


if __name__ == "__main__":
    main()