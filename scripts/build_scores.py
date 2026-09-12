"""Build deterministic, explainable opportunity scores for accounts."""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from src.scoring.icp import icp_score as technical_icp_score

WEIGHTS = {
    "icp": 0.30,
    "exposure": 0.20,
    "vulnerability": 0.20,
    "technology": 0.20,
    "recency": 0.10,
}


def bounded_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def logarithmic_score(value: int | float, midpoint: float) -> float:
    if value <= 0:
        return 0.0
    return bounded_score(100.0 * math.log1p(value) / math.log1p(midpoint))


def score_account(account: dict, reference_time: datetime) -> dict:
    unique_ports = account.get("unique_port_count") or 0
    database_count = account.get("exposed_database_count") or 0
    remote_access_count = account.get("exposed_remote_access_count") or 0
    critical_count = account.get("critical_vulnerability_observations") or 0
    high_count = account.get("high_vulnerability_observations") or 0
    vulnerability_count = account.get("vulnerability_count") or 0
    technology_count = len(account.get("technologies") or [])
    service_count = account.get("unique_service_count") or 0

    exposure_score = bounded_score(
        60.0 * logarithmic_score(unique_ports, 10) / 100.0
        + 20.0 * logarithmic_score(database_count, 3) / 100.0
        + 20.0 * logarithmic_score(remote_access_count, 3) / 100.0
    )
    vulnerability_score = bounded_score(
        55.0 * logarithmic_score(critical_count, 1) / 100.0
        + 30.0 * logarithmic_score(high_count, 3) / 100.0
        + 15.0 * logarithmic_score(vulnerability_count, 10) / 100.0
    )
    technology_score = bounded_score(
        70.0 * logarithmic_score(technology_count, 5) / 100.0
        + 30.0 * logarithmic_score(service_count, 5) / 100.0
    )

    last_seen = account.get("last_seen")
    if last_seen is None:
        recency_score = 0.0
    else:
        age_days = max(0.0, (reference_time - last_seen).total_seconds() / 86400.0)
        recency_score = bounded_score(100.0 * math.exp(-age_days / 30.0))

    icp_score = technical_icp_score(account)
    components = {
        "icp": icp_score,
        "exposure": exposure_score,
        "vulnerability": vulnerability_score,
        "technology": technology_score,
        "recency": recency_score,
    }
    opportunity_score = round(sum(WEIGHTS[name] * value for name, value in components.items()), 2)
    reasons = []
    if critical_count:
        reasons.append(f"{critical_count} critical vulnerability observations")
    if database_count:
        reasons.append(f"{database_count} exposed database observations")
    if remote_access_count:
        reasons.append(f"{remote_access_count} exposed remote-access observations")
    if account.get("eol_observation_count"):
        reasons.append(f"{account['eol_observation_count']} EOL observations")
    if unique_ports >= 10:
        reasons.append(f"{unique_ports} unique exposed ports")

    return {
        **account,
        "icp_score": icp_score,
        "exposure_score": exposure_score,
        "vulnerability_score": vulnerability_score,
        "technology_score": technology_score,
        "recency_score": recency_score,
        "opportunity_score": opportunity_score,
        "score_reasons": json.dumps(reasons, ensure_ascii=False),
    }


def build_scores(accounts: Path, output: Path) -> int:
    table = pq.read_table(accounts)
    accounts_rows = table.to_pylist()
    timestamps = [row["last_seen"] for row in accounts_rows if row.get("last_seen") is not None]
    reference_time = max(timestamps) if timestamps else datetime.now(timezone.utc)
    scored = [score_account(account, reference_time) for account in accounts_rows]
    pq.write_table(pa.Table.from_pylist(scored), output, compression="zstd")
    return len(scored)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accounts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = build_scores(args.accounts, args.output)
    print(f"Wrote {count:,} scored accounts to {args.output}")


if __name__ == "__main__":
    main()
