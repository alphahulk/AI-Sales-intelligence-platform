# Phase 3: Accounts and Signals

## Status

Completed.

## Account Aggregation

Command:

```powershell
python scripts/build_accounts.py data/curated/observations data/marts
```

Outputs:

- `data/marts/accounts.parquet`: rebuilt account rows; all registrable domains are retained.
- `data/marts/account_services.parquet`: rebuilt account-service rows.

Accounts are initially grouped by `registrable_domain`. No infrastructure-domain allowlist is hardcoded or used to discard data. Cloud and provider evidence is retained through `cloud_observation_count`, `identified_cloud_observation_count`, `cloud_providers`, and the original observation fields. Later scoring can classify infrastructure, customer, or uncertain accounts without losing source data.

Account attributes include first/last seen, observation count, unique IPs, hostnames, ports, services, countries, regions, cloud providers, technologies, services, vulnerability counts, critical/high vulnerability observations, EOL observations, exposed databases, and exposed remote access.

## Signals

Command:

```powershell
python scripts/build_signals.py data/marts/accounts.parquet data/marts/account_services.parquet data/marts/account_signals.parquet
```

Output:

- `data/marts/account_signals.parquet`: rebuilt signal rows.

Current deterministic rules:

| Signal | Rule | Severity |
| --- | --- | --- |
| `large_attack_surface` | 10 or more unique ports | medium |
| `critical_vulnerability` | CVSS at least 9.0 | critical |
| `high_vulnerability` | CVSS at least 7.0 and below 9.0 | high |
| `eol_product` | At least one EOL observation | medium |
| `exposed_database` | At least one database service | high |
| `exposed_remote_access` | At least one remote-access service | high |

Each signal has an account, signal identity, type, name, severity, value, confidence, timestamp, and human-readable description.

## Known Limitation

`evidence_observation_ids` are currently empty. The next improvement should carry representative observation IDs from aggregation into signals so every claim can link back to source evidence.