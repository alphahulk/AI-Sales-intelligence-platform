# Architecture

SignalDesk separates **evidence**, **ranking**, and **language**. The LLM never sees the raw warehouse and never computes the score.

```text
raw NDJSON (B2 file)
  → curated observation Parquet (bounded batches)
  → account + signal marts (DuckDB / PyArrow)
  → deterministic scores (rules)
  → Streamlit (filter, shortlist, qualify)
  → Gemini workflows (audit / meeting / outreach)
       ↳ JSONL traces + prompt files + evals
```

## Layers

| Layer | What | Storage |
|---|---|---|
| Raw | Immutable internet observations | Local `data/raw/` or original B2 object |
| Curated | One row per observation, normalized domains | `data/curated/observations` |
| Marts | One row per registrable domain + signals | `data/marts/*.parquet`, also B2 `marts/` |
| Scores | Weighted exposure / vuln / tech / recency / ICP | `scored_accounts.parquet` |
| Sales workspace | Saved domains, owner, status | Supabase Postgres (`DATABASE_URL`) or SQLite |
| AI | Prompt + evidence JSON → narrative | Google AI Studio; traces in `data/traces/llm.jsonl` |

Account identity is the **registrable domain**. Raw `org` is evidence, not a customer. Cloud and reverse-DNS noise is flagged, not treated as the buyer.

## Rule vs LLM split

**Rules** (`scripts/build_scores.py`, `scripts/build_signals.py`):

- Opportunity score = `0.30*ICP + 0.20*exposure + 0.20*vulnerability + 0.20*technology + 0.10*recency`.
- ICP is a **technical proxy** (org-like IP/service/tech/geo vs CDN-like cloud sprawl). Industry and headcount are not in the dump; if they appear later, `src/scoring/icp.py` can switch to a target-industry list.
- Signals are counters and named findings a seller can check.

**LLM** (`src/ai/generate.py`, `src/workflows/*`):

- Prospect audit (`prompts/audit/v2.md`)
- Meeting prep (`prompts/meeting_prep/v1.md`)
- Outreach (`prompts/outreach/v1.md`)
- Input is metrics + top 20 signals. Output is prose. Cache key is prompt version + model + prompt hash.

## Runtime

- **App:** Streamlit `app.py`. Marts load via DuckDB; `ensure_mart` downloads from Backblaze B2 S3 API when local files are missing (`region_name` taken from `B2_ENDPOINT`).
- **AI:** REST `generateContent` with `AI_API_KEY` / `GOOGLE_API_KEY`.
- **Eval:** `python evals/run_eval.py` scores audit v1 vs v2 with lexical precision/recall.

## Trade-offs

| Choice | Gain | Cost |
|---|---|---|
| Domain as account | Aggregable, matches how sellers search | Multi-brand orgs split; CDN domains inflate |
| Rules for ranking | Cheap, stable, `score_reasons` | No buyer-intent or true ICP |
| LLM after selection | Cost ceiling stays tiny | Quality depends on prompt + evals |
| Parquet + DuckDB | Laptop-scale 372k accounts | Not a live CDC warehouse |
| Supabase for shortlist | Shared sales state | App still needs env and network |

Phase notes: [docs/knowledge/README.md](knowledge/README.md). Cost: [docs/cost-model.md](cost-model.md).
