"""Build explainable account signals from the account and service marts."""

import argparse
import hashlib
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq


def signal_id(account_id: str, signal_name: str) -> str:
    return hashlib.sha1(f"{account_id}:{signal_name}".encode()).hexdigest()


def build_signals(accounts: Path, services: Path, output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    try:
        rows = connection.execute(
            """
            SELECT
                account_id,
                domain,
                observation_count,
                unique_port_count,
                vulnerability_count,
                critical_vulnerability_observations,
                high_vulnerability_observations,
                eol_observation_count,
                exposed_database_count,
                exposed_remote_access_count,
                last_seen
            FROM read_parquet(?)
            """,
            [str(accounts)],
        ).fetchall()
        signal_rows: list[dict] = []
        for row in rows:
            (
                account_id,
                domain,
                observation_count,
                unique_port_count,
                vulnerability_count,
                critical_count,
                high_count,
                eol_count,
                database_count,
                remote_access_count,
                last_seen,
            ) = row
            metrics = {
                "attack_surface_size": unique_port_count,
                "vulnerability_count": vulnerability_count,
                "critical_vulnerability_count": critical_count,
                "high_vulnerability_count": high_count,
                "eol_observation_count": eol_count,
                "exposed_database_count": database_count,
                "exposed_remote_access_count": remote_access_count,
            }
            candidates = [
                ("attack_surface", "large_attack_surface", unique_port_count >= 10, unique_port_count, "Account exposes 10 or more distinct ports."),
                ("vulnerability", "critical_vulnerability", critical_count > 0, critical_count, "Account has observations with CVSS at or above 9.0."),
                ("vulnerability", "high_vulnerability", high_count > 0, high_count, "Account has observations with CVSS from 7.0 to below 9.0."),
                ("technology", "eol_product", eol_count > 0, eol_count, "Account has one or more end-of-life observations."),
                ("exposure", "exposed_database", database_count > 0, database_count, "Account exposes a detected database service."),
                ("exposure", "exposed_remote_access", remote_access_count > 0, remote_access_count, "Account exposes a detected remote-access service."),
            ]
            for signal_type, signal_name, present, value, description in candidates:
                if not present:
                    continue
                severity = "critical" if signal_name == "critical_vulnerability" else "high" if signal_type in {"vulnerability", "exposure"} else "medium"
                signal_rows.append(
                    {
                        "account_id": account_id,
                        "domain": domain,
                        "signal_id": signal_id(account_id, signal_name),
                        "signal_type": signal_type,
                        "signal_name": signal_name,
                        "severity": severity,
                        "observed_at": last_seen,
                        "first_seen": None,
                        "last_seen": last_seen,
                        "value": float(value),
                        "evidence_observation_ids": [],
                        "confidence": 0.9,
                        "description": description,
                        "observation_count": observation_count,
                        "metrics_json": str(metrics),
                    }
                )
        table = pa.Table.from_pylist(signal_rows)
        pq.write_table(table, output, compression="zstd")
        return len(signal_rows)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accounts", type=Path)
    parser.add_argument("services", type=Path, help="reserved for service evidence extensions")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    count = build_signals(args.accounts, args.services, args.output)
    print(f"Wrote {count:,} account signals to {args.output}")


if __name__ == "__main__":
    main()
