"""Re-run labelled prospect-audit checks against prompt v1 and v2."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from evals.judge import aggregate, score_output
from src.ai.generate import build_account_evidence, compose_prompt
from src.ai.provider import ProviderError, complete, configured, model_name
from src.ai.tracing import estimate_cost_usd

DATASET = Path(__file__).parent / "datasets" / "prospect_audit.jsonl"
PROMPTS = {
    "audit/v1": ROOT / "prompts" / "audit" / "v1.md",
    "audit/v2": ROOT / "prompts" / "audit" / "v2.md",
}
RESULTS_DIR = Path(__file__).parent / "results"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate_version(version: str, cases: list[dict], *, live: bool) -> dict:
    prompt_path = PROMPTS[version]
    scored = []
    tokens_in = tokens_out = 0
    cost = 0.0
    for case in cases:
        evidence = build_account_evidence(case["account"], case.get("signals") or [], "prospect_audit")
        prompt = compose_prompt(prompt_path, evidence)
        if live:
            completion = complete(prompt)
            text = completion.text
            tokens_in += completion.input_tokens
            tokens_out += completion.output_tokens
            cost += estimate_cost_usd(completion.model, completion.input_tokens, completion.output_tokens)
        else:
            text = case.get("fixture_output") or ""
        judged = score_output(text, case["expected"])
        judged["id"] = case["id"]
        scored.append(judged)
    summary = aggregate(scored)
    summary["prompt_version"] = version
    summary["live"] = live
    summary["input_tokens"] = tokens_in
    summary["output_tokens"] = tokens_out
    summary["cost_usd"] = round(cost, 6)
    summary["failures"] = [row["id"] for row in scored if not row["passed"]]
    summary["case_results"] = scored
    return summary


def delta(current: dict, previous: dict | None) -> dict:
    if not previous:
        return {}
    keys = ("precision", "recall", "pass_rate")
    return {key: round(current.get(key, 0) - previous.get(key, 0), 4) for key in keys}


def main() -> int:
    parser = argparse.ArgumentParser(description="Prospect-audit eval harness")
    parser.add_argument("--offline", action="store_true", help="Score fixture_output fields only; no Gemini calls")
    args = parser.parse_args()
    cases = load_cases()
    live = configured() and not args.offline
    if not live and not args.offline and not configured():
        print("No AI_API_KEY / GOOGLE_API_KEY. Re-run after setting a key, or pass --offline.")
        return 1

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    previous_path = RESULTS_DIR / "previous.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else None
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model_name() if live else "offline-fixture",
        "dataset": str(DATASET.relative_to(ROOT)),
        "cases": len(cases),
        "versions": {},
    }
    print(f"Loaded {len(cases)} evaluation cases ({'live Gemini' if live else 'offline fixtures'})")
    for version in ("audit/v1", "audit/v2"):
        try:
            summary = evaluate_version(version, cases, live=live)
        except ProviderError as error:
            print(f"{version} failed: {error}")
            return 1
        prior = (previous or {}).get("versions", {}).get(version)
        summary["vs_previous"] = delta(summary, prior)
        report["versions"][version] = summary
        print(
            f"{version}: precision={summary['precision']:.3f} recall={summary['recall']:.3f} "
            f"pass_rate={summary['pass_rate']:.3f} cost=${summary['cost_usd']:.4f} "
            f"delta={summary['vs_previous'] or 'n/a'}"
        )
        if summary["failures"]:
            print(f"  failures: {', '.join(summary['failures'])}")

    v1 = report["versions"]["audit/v1"]
    v2 = report["versions"]["audit/v2"]
    report["winner"] = "audit/v2" if (v2["pass_rate"], v2["recall"]) >= (v1["pass_rate"], v1["recall"]) else "audit/v1"
    print(f"winner: {report['winner']}")

    latest = RESULTS_DIR / "latest.json"
    if latest.exists():
        previous_path.write_text(latest.read_text(encoding="utf-8"), encoding="utf-8")
    slim = json.loads(json.dumps(report))
    for version in slim["versions"].values():
        version.pop("case_results", None)
    latest.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    (RESULTS_DIR / "latest.full.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {latest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
