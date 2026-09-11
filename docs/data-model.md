# Data Model

The pipeline has three durable layers:

1. `data/raw/`: immutable source files.
2. `data/curated/observations/`: one normalized row per source observation.
3. `data/marts/`: account-level and signal-level datasets for the application.

Phase 1 reports are evidence for schema decisions. They are generated under `reports/` and are not committed by default.