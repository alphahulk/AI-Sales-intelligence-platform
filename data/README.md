# Data

Keep raw and generated datasets out of source control.

- `data/raw/`: source downloads such as the Zstandard NDJSON file.
- `data/processed/`: normalized observations and account Parquet files.

The pipeline is reproducible with:

```powershell
python scripts/ingest.py data/raw/b2_download_file_by_id data/processed/observations.parquet
python scripts/aggregate.py data/processed/observations.parquet data/processed/accounts.parquet
```