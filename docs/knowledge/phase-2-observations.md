# Phase 2: Curated Observations

## Status

Completed and validated.

## Command

```powershell
python scripts/build_observations.py b2_download_file_by_id data/curated/observations --batch-size 50000
python scripts/validate_data.py data/curated/observations
```

## Result

- Rows written: 10,113,894.
- Parquet parts: 203.
- Batch size: 50,000 rows.
- Required-column validation: passed.

## Curated Contract

Each row represents one source observation and includes:

- Identity: `observation_id`, `timestamp`, `ip`, `ip_str`, `ipv6`, `asn`.
- Naming: `domain`, `domains`, `hostname`, `hostnames`, `registrable_domains`.
- Location: country, region, city, latitude, longitude.
- Exposure: port, transport, service category, product, version, OS.
- HTTP: status, title, server, host, redirects, security.txt, HTML flag.
- SSL: presence, version, subject, issuer, expiry.
- Cloud: presence, provider, region, service.
- Organization: raw `org`, `canonical_org`, and `isp`.
- Tags and CPE: arrays, counts, and EOL flag.
- Vulnerability: presence, count, IDs, maximum CVSS, known-exploit flag.
- Detection: technologies, services, service counts, database and remote-access counts.
- Audit fields: raw tags, vulnerabilities, HTTP, and SSL JSON strings.

The raw Zstandard file is not modified or discarded.