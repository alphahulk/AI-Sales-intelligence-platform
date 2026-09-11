# Phase 1: Deep Profiling

## Status

Completed with a uniform reservoir sample of 8,000 records from the full 10,113,894-record stream.

## Source Facts

- Source format: Zstandard-compressed newline-delimited JSON.
- Compressed source size: approximately 11.25 GB.
- Total records: 10,113,894.
- Sample method: reservoir sampling across the complete stream, seed `42`.

## Vulnerabilities

The sample showed 146 records with vulnerability data and 5,103 CVE detail objects.

Observed fields included:

- `cvss`
- `cvss_version`
- `cvss_v2`
- `references`
- `summary`
- `verified`
- `epss`
- `ranking_epss`
- `kev`
- `ransomware_campaign`

This supports curated fields for vulnerability count, CVE IDs, maximum CVSS, and known-exploit/KEV indicators.

## Domain and Hostname Coverage

In the sample:

- 5,642 records had domains.
- 2,358 records had no domains, approximately 29.5%.
- Estimated domain coverage was approximately 70.5%.
- Maximum domains in one record: 115.
- Maximum hostnames in one record: 347.

## Infrastructure Noise

Cloud/PTR patterns appeared frequently:

- 1,932 sampled records matched known cloud/PTR patterns.
- 1,747 had exactly `googleusercontent.com` as a domain.
- Common infrastructure domains included `amazonaws.com`, `cloudfront.net`, `scw.cloud`, and `linodeusercontent.com`.

Therefore `org` must not be treated as the customer account by itself. Account resolution must flag or exclude infrastructure domains.

## Tags

Most frequent sampled tags included:

```text
cdn, cloud, proxy, self-signed, eol-product, honeypot, vpn, database, starttls, iot
```

Tags remain as an array plus derived fields such as `tag_count` and EOL flags.

## Technologies and Ports

The detector sample was intentionally broad. No candidate detector exceeded 100 occurrences in the 8,000-record sample. The most common candidates included `ntlm`, `snmp`, `ssh`, `pptp`, `ntp`, and `dns`.

The port distribution was highly long-tailed. Common ports included `443`, `80`, `8080`, `2086`, `554`, and `8880`, so service categorization should combine known-port mappings with product/detector evidence.

## Reports

Generated reports live under `reports/` when the profiling command is run:

```powershell
python scripts/profile_nested_fields.py b2_download_file_by_id reports/nested_profile.json --sample-size 8000 --seed 42
```