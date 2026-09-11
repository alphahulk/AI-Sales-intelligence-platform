"""Validate curated observation Parquet files."""

import argparse
from pathlib import Path

import pyarrow.dataset as ds

REQUIRED_COLUMNS = {
    "observation_id",
    "timestamp",
    "ip_str",
    "port",
    "registrable_domains",
    "detected_technologies",
    "detected_services",
    "vuln_count",
}


def validate(path: Path) -> dict[str, object]:
    dataset = ds.dataset(path, format="parquet")
    schema_names = set(dataset.schema.names)
    missing_columns = sorted(REQUIRED_COLUMNS - schema_names)
    row_count = dataset.count_rows()
    return {
        "path": str(path),
        "row_count": row_count,
        "part_count": len(list(path.glob("part-*.parquet"))) if path.is_dir() else 1,
        "missing_required_columns": missing_columns,
        "valid": not missing_columns and row_count > 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    result = validate(args.path)
    for key, value in result.items():
        print(f"{key}: {value}")
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
