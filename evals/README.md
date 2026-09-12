# Prospect audit evals

Hand-labelled checks for the core LLM feature. The judge is lexical on purpose: required evidence strings must appear; invented firmographics must not.

Live Gemini is optional. The free tier is about **20 `generateContent` calls per minute**; 25 cases × 2 prompt versions will 429 if you burst. Space-out is built into the harness (`time.sleep(4)` plus retries). Re-run when quota recovers:

```powershell
python evals/run_eval.py
```

Compares `prompts/audit/v1.md` vs `prompts/audit/v2.md` on `evals/datasets/prospect_audit.jsonl` (25 cases). Writes `evals/results/latest.json` and, on the next run, deltas vs `evals/results/previous.json`.

Offline (no API; empty outputs unless you add `fixture_output` on a case):

```powershell
python evals/run_eval.py --offline
```
