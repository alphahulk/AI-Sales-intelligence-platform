"""Build compact, evidence-linked JSONL context for AI workflows."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb


def sql_literal(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def build_context(
    scored_accounts: Path,
    signals: Path,
    observations: Path,
    output: Path,
    limit: int,
    evidence_per_account: int,
) -> int:
    connection = duckdb.connect()
    try:
        scored = connection.execute(
            f"""
            SELECT *
            FROM read_parquet({sql_literal(scored_accounts)})
            ORDER BY opportunity_score DESC, domain
            LIMIT {limit}
            """
        ).fetchall()
        scored_columns = [item[0] for item in connection.description]
        selected = [dict(zip(scored_columns, row)) for row in scored]
        domains = [row["domain"] for row in selected]
        if not domains:
            output.write_text(encoding="utf-8", data="")
            return 0

        escaped_domains = ", ".join("'" + str(domain).replace("'", "''") + "'" for domain in domains)
        signal_rows = connection.execute(
            f"""
            SELECT *
            FROM read_parquet({sql_literal(signals)})
            WHERE domain IN ({escaped_domains})
            ORDER BY domain, severity, signal_name
            """
        ).fetchall()
        signal_columns = [item[0] for item in connection.description]
        signals_by_domain: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in signal_rows:
            signal = dict(zip(signal_columns, row))
            signals_by_domain[signal["domain"]].append(signal)

        evidence_rows = connection.execute(
            f"""
            WITH evidence AS (
                SELECT
                    unnest(registrable_domains) AS domain,
                    observation_id,
                    timestamp,
                    ip_str,
                    port,
                    service_category,
                    product,
                    version,
                    vuln_count,
                    vuln_max_cvss,
                    cloud_provider,
                    detected_technologies
                FROM read_parquet({sql_literal(observations)})
            ), ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY domain
                        ORDER BY vuln_max_cvss DESC NULLS LAST, timestamp DESC
                    ) AS evidence_rank
                FROM evidence
                WHERE domain IN ({escaped_domains})
            )
            SELECT * FROM ranked WHERE evidence_rank <= {evidence_per_account}
            """
        ).fetchall()
        evidence_columns = [item[0] for item in connection.description]
        evidence_by_domain: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in evidence_rows:
            evidence = dict(zip(evidence_columns, row))
            domain = evidence.pop("domain")
            evidence.pop("evidence_rank", None)
            if domain in domains and len(evidence_by_domain[domain]) < evidence_per_account:
                evidence_by_domain[domain].append(evidence)

        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as output_file:
            for account in selected:
                domain = account["domain"]
                context = {
                    "account": {
                        "account_id": account["account_id"],
                        "domain": domain,
                        "first_seen": account["first_seen"],
                        "last_seen": account["last_seen"],
                    },
                    "metrics": {
                        key: account[key]
                        for key in (
                            "observation_count",
                            "unique_ip_count",
                            "unique_hostname_count",
                            "unique_port_count",
                            "unique_service_count",
                            "vulnerability_count",
                            "critical_vulnerability_observations",
                            "high_vulnerability_observations",
                            "eol_observation_count",
                            "exposed_database_count",
                            "exposed_remote_access_count",
                            "cloud_observation_count",
                            "identified_cloud_observation_count",
                        )
                    },
                    "scores": {
                        key: account[key]
                        for key in (
                            "icp_score",
                            "exposure_score",
                            "vulnerability_score",
                            "technology_score",
                            "recency_score",
                            "opportunity_score",
                        )
                    },
                    "signals": signals_by_domain[domain],
                    "evidence": evidence_by_domain[domain],
                }
                output_file.write(json.dumps(context, ensure_ascii=False, default=str) + "\n")
        return len(selected)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scored_accounts", type=Path)
    parser.add_argument("signals", type=Path)
    parser.add_argument("observations", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--evidence-per-account", type=int, default=5)
    args = parser.parse_args()
    if args.limit <= 0 or args.evidence_per_account <= 0:
        parser.error("--limit and --evidence-per-account must be greater than zero")
    count = build_context(
        args.scored_accounts,
        args.signals,
        args.observations,
        args.output,
        args.limit,
        args.evidence_per_account,
    )
    print(f"Wrote {count:,} compact account contexts to {args.output}")


if __name__ == "__main__":
    main()
