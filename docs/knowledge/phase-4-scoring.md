# Phase 4: Deterministic Scoring

## Status

Implemented and generated for all `372,409` accounts.

Output:

- `data/marts/scored_accounts.parquet`
- Minimum opportunity score: `42.45`
- Average opportunity score: `46.13`
- Maximum opportunity score: `77.0`

## Intended Score

```text
opportunity_score =
    ICP score           * 0.30
  + exposure score      * 0.20
  + vulnerability score * 0.20
  + technology score    * 0.20
  + recency score       * 0.10
```

All component scores should be normalized to 0-100 before weighting.

Current component logic uses available account evidence:

- Exposure: unique ports, exposed database observations, and exposed remote-access observations.
- Vulnerability: critical, high, and total vulnerability observations.
- Technology: detected technology and service counts.
- Recency: exponential decay from the latest observed timestamp in the dataset.
- ICP: technical proxy in `src/scoring/icp.py` (footprint size, services, technologies, countries). Not firmographic industry/headcount — those fields are absent. Rebuild `scored_accounts.parquet` after changing it.

Each scored row also contains `score_reasons`, a JSON list of the evidence that contributed to the ranking.

## Planned Output

```text
data/marts/scored_accounts.parquet
```

Expected fields:

- `icp_score`
- `exposure_score`
- `vulnerability_score`
- `technology_score`
- `recency_score`
- `opportunity_score`

Scoring must remain deterministic, inspectable, and independent of the LLM. The LLM should explain and prioritize evidence rather than invent or calculate the core score.