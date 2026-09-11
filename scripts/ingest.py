"""Normalize compressed observations into Parquet."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.parser import parse_observation
from src.ingestion.reader import read_records
from src.ingestion.writer import write_parquet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    count = write_parquet((parse_observation(record) for record in read_records(args.input)), args.output)
    print(f"Wrote {count:,} observations to {args.output}")


if __name__ == "__main__":
    main()