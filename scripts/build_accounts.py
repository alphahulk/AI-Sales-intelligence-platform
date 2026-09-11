"""Aggregate curated observations into account and service Parquet marts."""

import argparse
from pathlib import Path

import duckdb


ACCOUNT_QUERY = """
WITH observations AS (
    SELECT * FROM read_parquet(?)
), account_observations AS (
    SELECT
        unnest(registrable_domains) AS domain,
        *
    FROM observations
    WHERE registrable_domains IS NOT NULL
      AND len(registrable_domains) > 0
)
SELECT
    domain AS account_id,
    domain,
    min(try_cast(timestamp AS TIMESTAMP)) AS first_seen,
    max(try_cast(timestamp AS TIMESTAMP)) AS last_seen,
    count(*) AS observation_count,
    count(DISTINCT ip_str) AS unique_ip_count,
    count(DISTINCT hostname) AS unique_hostname_count,
    count(DISTINCT port) AS unique_port_count,
    count(DISTINCT service_category) AS unique_service_count,
    count(*) FILTER (WHERE cloud_present) AS cloud_observation_count,
    count(*) FILTER (WHERE cloud_present AND cloud_provider IS NOT NULL) AS identified_cloud_observation_count,
    list(DISTINCT country_code) FILTER (WHERE country_code IS NOT NULL) AS countries,
    list(DISTINCT region_code) FILTER (WHERE region_code IS NOT NULL) AS regions,
    list(DISTINCT cloud_provider) FILTER (WHERE cloud_provider IS NOT NULL) AS cloud_providers,
    list_distinct(flatten(list(detected_technologies))) AS technologies,
    list_distinct(flatten(list(detected_services))) AS services,
    sum(vuln_count) AS vulnerability_count,
    sum(CASE WHEN vuln_max_cvss >= 9.0 THEN 1 ELSE 0 END) AS critical_vulnerability_observations,
    sum(CASE WHEN vuln_max_cvss >= 7.0 AND vuln_max_cvss < 9.0 THEN 1 ELSE 0 END) AS high_vulnerability_observations,
    sum(CASE WHEN has_eol_tag THEN 1 ELSE 0 END) AS eol_observation_count,
    sum(database_service_count) AS exposed_database_count,
    sum(remote_access_service_count) AS exposed_remote_access_count
FROM account_observations
GROUP BY domain
"""

SERVICE_QUERY = """
WITH observations AS (
    SELECT
        *
    FROM read_parquet(?)
)
SELECT
    domain_row.domain AS account_id,
    domain_row.domain,
    service_row.service,
    count(*) AS observation_count,
    min(try_cast(observation.timestamp AS TIMESTAMP)) AS first_seen,
    max(try_cast(observation.timestamp AS TIMESTAMP)) AS last_seen
FROM observations AS observation
CROSS JOIN UNNEST(observation.registrable_domains) AS domain_row(domain)
CROSS JOIN UNNEST(observation.detected_services) AS service_row(service)
WHERE domain_row.domain IS NOT NULL
GROUP BY domain_row.domain, service_row.service
"""


def sql_literal(value: Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def build_accounts(observations: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    try:
        source = sql_literal(observations)
        account_query = ACCOUNT_QUERY
        account_query = account_query.replace("read_parquet(?)", f"read_parquet({source})")
        service_query = SERVICE_QUERY.replace("read_parquet(?)", f"read_parquet({source})")
        connection.execute(
            f"COPY ({account_query}) TO {sql_literal(output_dir / 'accounts.parquet')} (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        connection.execute(
            f"COPY ({service_query}) TO {sql_literal(output_dir / 'account_services.parquet')} (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_accounts(args.observations, args.output)
    print(f"Wrote account marts to {args.output}")


if __name__ == "__main__":
    main()
