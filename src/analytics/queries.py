"""Reusable DuckDB queries."""

ACCOUNT_QUERY = """
SELECT
    canonical_org,
    count(*) AS observation_count,
    list(DISTINCT ip) AS ips,
    max(timestamp) AS last_observed_at
FROM read_parquet(?)
WHERE canonical_org IS NOT NULL
GROUP BY canonical_org
ORDER BY observation_count DESC
"""