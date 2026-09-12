# Cost Model

Deterministic pipeline cost is **local compute** (ingest, DuckDB aggregation, scoring). LLM cost is incurred only after a human or filter selects an account.

## Model choice

| Task | Model | Why |
|---|---|---|
| Opportunity score, signals, ICP proxy | Rules (`scripts/build_scores.py`) | Repeatable, free, explainable |
| Prospect audit, meeting brief, outreach | `gemini-3.6-flash` (Google AI Studio) | Cheap generation; judgement stays on evidence JSON |
| Eval judge | Lexical precision/recall | No second model in the loop |

Approximate list prices used in traces (`src/ai/tracing.py`): **$0.15 / 1M input tokens**, **$0.60 / 1M output tokens** for Flash-class Gemini. Traces store `cost_usd` per call; treat that as a ceiling estimate, not a bill.

## Tokens × volume × frequency

Measured shape from the prompt pack (scores + ≤20 signals + `prompts/audit/v2.md`): about **1,200–2,000 input tokens** and **400–800 output tokens** per audit.

Using midpoints **1,600 in / 600 out**:

```text
cost_per_audit ≈ (1600/1e6)*0.15 + (600/1e6)*0.60
               ≈ $0.00024 + $0.00036
               ≈ $0.00060
```

Assumed production mix for a 10-person SDR team:

| Workflow | Calls / rep / day | Team / day | Uncached $ / day |
|---|---|---|---|
| Prospect audit | 20 | 200 | $0.12 |
| Meeting prep | 8 | 80 | $0.05 |
| Outreach draft | 15 | 150 | $0.09 |
| **Total** | | **430** | **~$0.26** |

Monthly uncached ≈ **$5.50**. With a 40% cache hit rate (same domain + prompt version + model): **~$3.30 / month**.

## Ceiling

Set a hard monthly ceiling of **$25** for LLM (≈ 4× the modelled team usage). Enforce by:

1. Never scoring the 372k-account mart with an LLM.
2. Calling Gemini only from the three account workflows.
3. Caching `(prompt_version, model, prompt hash)` in process.
4. Tracing every call; alert if rolling 24h `cost_usd` > $2.

If evals show Flash inventing firmographics above ~15% of cases, route **failed eval slices** to a stronger model for those prompts only — not for ranking.
