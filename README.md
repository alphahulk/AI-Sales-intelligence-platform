# AI Sales Intelligence

A streaming data pipeline for turning large internet-observation datasets into account-level sales signals.

## Pipeline

```text
Zstandard NDJSON -> normalized observations -> Parquet -> DuckDB accounts -> deterministic scores -> workflows
```

## Usage

Install dependencies in the project environment:

```powershell
python -m pip install -r requirements.txt
```

Profile the source dataset:

```powershell
python scripts/profile_dataset.py data/raw/b2_download_file_by_id --top 10
```

Run the deep Phase 1 profile with uniform reservoir sampling:

```powershell
python scripts/profile_nested_fields.py data/raw/b2_download_file_by_id reports/nested_profile.json --sample-size 8000 --seed 42
```

This writes nested-field, tags, technologies, ports, products, vulnerabilities, organizations, and dataset reports under `reports/`. The sample is drawn across the entire stream rather than from the first records.

Build observations and accounts:

```powershell
python scripts/build_observations.py data/raw/b2_download_file_by_id data/curated/observations
python scripts/validate_data.py data/curated/observations
python scripts/build_accounts.py data/curated/observations data/marts
python scripts/build_signals.py data/marts/accounts.parquet data/marts/account_services.parquet data/marts/account_signals.parquet
python scripts/build_scores.py data/marts/accounts.parquet data/marts/scored_accounts.parquet
```

The raw file is never modified. Curated observations are written in bounded batches as `part-*.parquet`; only after validation should account marts be built. Account aggregation retains all registrable domains and exposes cloud evidence instead of using a hardcoded exclusion list. Signal generation remains deterministic and explainable.

The AI and Streamlit layers are deliberately isolated from ingestion and deterministic scoring.

## App

```powershell
streamlit run app.py
```

Requires `.env` with optional `DATABASE_URL`, `B2_*`, and Google AI Studio `AI_API_KEY` (see `.env.example`).

## Evals

```powershell
python evals/run_eval.py
```

25 labelled prospect-audit cases, prompt v1 vs v2, precision/recall. Details in [evals/README.md](evals/README.md). Planning, architecture, cost, and build notes live under `docs/`.