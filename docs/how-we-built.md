# How We Built It

This was an **agentic loop in Cursor**: inspect the Censys-style dump, write a streaming pipeline, only then add UI and Gemini. The model did not replace judgement on schema or scoring weights.

## Dev loop

1. Profile nested JSON (ports, vulns, tags, orgs) with reservoir sampling so we did not invent columns.
2. Stream raw → Parquet observations with bounded memory; validate; aggregate to domain marts.
3. Score with explicit weights and `score_reasons`.
4. Streamlit radar + saved accounts (Supabase).
5. One LLM path (prospect audit), then meeting/outreach, traces, evals, skill file.

Cursor was fastest on boilerplate (Streamlit layout, boto3 client, eval harness). It was slowest when it guessed B2 auth: mixing master vs bucket keys and signing `us-east-1` against `s3.us-east-005` produced `SignatureDoesNotMatch` until the endpoint region was set. Widget reruns on every qualification keystroke were another “generated UI” miss — `st.form` was the human fix.

## Where AI saved time

- Drafting DuckDB/Parquet job structure and score-component formulas.
- Turning architecture decisions into the Streamlit information architecture (radar → analytics → AI workspace).
- Expanding the eval case list once the judge contract (must_mention / must_not_mention) existed.

## Where it cost more than doing it by hand

- Storage wiring (B2 signature, bucket name `salesmarts` vs typos).
- Streamlit session semantics (selection + forms + `value=` resetting fields).
- Prompt/model IDs (`gemini-2.5-flash` 404 for new Studio keys → `gemini-3.6-flash`).

## Weakness to flag to a teammate

**ICP is a constant 50**, and the audit eval is **lexical** (substring precision/recall), not a semantic grader. v2 still can paraphrase around a required CVE string or mention an industry. Do not treat `evals/results/latest.json` as a customer-quality bar without reading failures. Also: qualification and LLM output are not written back to the mart — only to Supabase notes if the seller pastes them.

Agentic tools used: Cursor (Grok) in-repo, Streamlit locally, Google AI Studio for Gemini, Backblaze B2 for marts, Supabase Postgres for the shortlist.
