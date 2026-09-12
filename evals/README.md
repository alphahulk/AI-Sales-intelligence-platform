# Prospect audit evals

Hand-labelled checks for the core LLM feature. The judge is lexical on purpose: required evidence strings must appear; invented firmographics must not.

```powershell
python evals/run_eval.py
```

Compares `prompts/audit/v1.md` vs `prompts/audit/v2.md` on `evals/datasets/prospect_audit.jsonl` (25 cases). Writes `evals/results/latest.json` and, on the next run, deltas vs `evals/results/previous.json`.

Offline (no API; empty outputs unless you add `fixture_output` on a case):

```powershell
python evals/run_eval.py --offline
```
