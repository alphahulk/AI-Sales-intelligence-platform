# Project Knowledge

This directory is the durable implementation record for the data pipeline. Update the relevant phase note after each phase finishes.

## Knowledge Map

- [phase-1-profiling.md](phase-1-profiling.md): measured source-data facts and schema decisions.
- [phase-2-observations.md](phase-2-observations.md): curated observation ETL and Parquet contract.
- [phase-3-accounts-and-signals.md](phase-3-accounts-and-signals.md): DuckDB marts and deterministic signals.
- [phase-4-scoring.md](phase-4-scoring.md): scoring work to be completed next.
- [architecture-decisions.md](architecture-decisions.md): cross-phase design decisions and caveats.
- [phase-update-template.md](phase-update-template.md): template for future phase updates.

## Layer Model

```text
RAW observations
    -> CURATED observations
    -> ACCOUNT marts
    -> SIGNALS and scores
    -> LLM workflows and UI
```

Raw records remain immutable. Curated rows are evidence. Account rows are aggregation. Signals and scores are derived decision support.