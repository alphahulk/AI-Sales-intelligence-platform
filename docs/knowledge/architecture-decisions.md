# Architecture Decisions

## Three Durable Layers

```text
RAW -> CURATED OBSERVATIONS -> ACCOUNT MARTS -> SIGNALS/SCORES
```

Raw data is immutable source evidence. Curated observations are one-row-per-record normalized evidence. Account marts are one-row-per-domain aggregation. Signals and scores are derived decision support.

## Account Identity

Registrable domains are the first account key. Raw `org` is retained for evidence but is not considered a customer identity by itself. Cloud-provider and reverse-DNS infrastructure must be filtered or flagged.

## Parquet

Parquet is used for compressed, column-oriented analytical storage. It allows DuckDB to scan only the columns needed by a query without loading the complete dataset into memory.

## LLM Boundary

The LLM must receive account metrics, deterministic signals, and a small set of source evidence. It must not receive thousands of raw observations as its primary input.

## Schema Evolution

The Phase 1 reports are evidence for schema decisions. New detectors or fields should be added after profiling rather than hardcoding every raw column into the curated table.