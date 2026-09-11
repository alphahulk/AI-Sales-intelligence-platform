# Data Pipeline

`reader.py` streams Zstandard NDJSON, `parser.py` extracts stable fields, and `writer.py` writes compressed Parquet in batches. DuckDB reads the resulting Parquet without requiring a separate database server.

Phase 2 uses `scripts/build_observations.py` to write one normalized observation row per source record under `data/curated/observations/`. `scripts/validate_data.py` checks required columns, row count, and readable Parquet parts before aggregation.

Phase 1 profiling showed that account resolution must distinguish customer domains from infrastructure identities. `googleusercontent.com`, cloud-provider PTR names, and records without domains should be represented as evidence and classified later; they must not be silently discarded. `org` is evidence about the network owner, not proof of the customer account.