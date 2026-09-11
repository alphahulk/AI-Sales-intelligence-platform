"""Build account-level data from observation Parquet."""

from pathlib import Path

import duckdb

from src.analytics.queries import ACCOUNT_QUERY


def aggregate_accounts(observations: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    try:
        query = ACCOUNT_QUERY.replace("?", "'" + str(observations).replace("'", "''") + "'", 1)
        connection.execute(f"COPY ({query}) TO ? (FORMAT PARQUET)", [str(output)])
    finally:
        connection.close()