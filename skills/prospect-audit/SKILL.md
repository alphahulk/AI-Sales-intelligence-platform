---
name: prospect-audit
description: >-
  Produce an evidence-linked cybersecurity prospect audit from deterministic
  account scores and signals. Use when generating a prospect audit, account
  briefing, or sales qualification write-up from SignalDesk evidence — not when
  recalculating opportunity scores or scanning raw observations.
---

# Prospect Audit

Turn one scored domain into a sales-usable audit. Ranking is already done by rules. This skill only **explains** evidence.

## When to trigger

- User asks for a prospect audit, account briefing, or “why this company.”
- Streamlit **Generate prospect audit** (or the Python invocation below).
- Do **not** trigger to compute `opportunity_score`, scan raw NDJSON, or invent firmographics.

## Inputs

| Field | Source | Required |
|---|---|---|
| `account` | Row from `data/marts/scored_accounts.parquet` | Yes |
| `signals` | Rows from `data/marts/account_signals.parquet` for that domain (top 20) | Yes (may be empty) |
| Prompt file | `prompts/audit/v2.md` (current) or `prompts/audit/v1.md` | Yes |
| Model | `AI_MODEL` (default `gemini-3.6-flash`) | Yes |

The workflow packs scores, footprint counts, `score_reasons`, and signals in `src.workflows.audit.build_audit_input`. Do not send raw observations.

## Outputs

Markdown audit that:

1. States the domain and the **precomputed** opportunity score.
2. Lists observed risks (vulns, exposed data stores, remote access, EOL) with signal names.
3. Separates **observed** vs **hypothesis** vs **missing**.
4. Suggests sales next steps that follow the evidence.

Must not invent industry, headcount, named contacts, or a confirmed customer relationship.

Traces: `data/traces/llm.jsonl` with `workflow=prospect_audit`, `prompt_version`, model, tokens, `cost_usd`, latency.

## Guardrails

- Scores stay deterministic (`scripts/build_scores.py`).
- If a fact is not in the JSON evidence, say it is missing.
- Prefer `audit/v2` in production. Compare versions with `python evals/run_eval.py`.

## Dependent prompts

- [prompts/audit/v2.md](../../prompts/audit/v2.md) — production
- [prompts/audit/v1.md](../../prompts/audit/v1.md) — eval baseline

## Worked example

```powershell
python -c "from src.workflows.audit import run_prospect_audit; print(run_prospect_audit({'domain':'example.com','opportunity_score':71.2,'exposure_score':60,'vulnerability_score':80,'technology_score':40,'recency_score':50,'score_reasons':['2 critical vulnerability observations'],'critical_vulnerability_observations':2}, [{'signal_type':'vulnerability','signal_name':'CVE-2024-4577','severity':'critical','description':'PHP CGI argument injection','confidence':0.9}]).text)"
```

In the app: Opportunity radar → select a row → AI workspace → **Prospect audit** → **Generate prospect audit**.

## Related

- Meeting prep: `prompts/meeting_prep/v1.md` via `src.workflows.meeting.run_meeting_prep`
- Outreach: `prompts/outreach/v1.md` via `src.workflows.outreach.run_outreach_draft`
