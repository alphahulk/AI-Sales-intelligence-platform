"""Aggregate observation Parquet into account Parquet with DuckDB."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.aggregation import aggregate_accounts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    aggregate_accounts(args.observations, args.output)
    print(f"Wrote account dataset to {args.output}")


if __name__ == "__main__":
    main()