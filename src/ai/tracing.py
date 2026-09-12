"""JSONL traces for every LLM call."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TRACE_PATH = ROOT / "data" / "traces" / "llm.jsonl"

# Approximate Gemini Flash list prices (USD per 1M tokens). Used for ceilings, not billing.
RATES_PER_MILLION = {
    "gemini-3.6-flash": (0.15, 0.60),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-1.5-flash": (0.075, 0.30),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    input_rate, output_rate = RATES_PER_MILLION.get(model, (0.15, 0.60))
    return round((input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate, 6)


def append_trace(record: dict[str, Any], path: Path | None = None) -> Path:
    target = path or TRACE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **record,
    }
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return target
