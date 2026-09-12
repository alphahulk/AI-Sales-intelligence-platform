"""JSONL traces for every LLM call."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TRACE_PATH = ROOT / "data" / "traces" / "llm.jsonl"

# Approximate list prices (USD per 1M tokens). Used for ceilings, not billing.
RATES_PER_MILLION = {
    # Gemini models
    "gemini-3.6-flash": (0.15, 0.60),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-1.5-flash": (0.075, 0.30),
    # Claude models
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-sonnet-20240620": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (1.00, 5.00),
    "claude-3-opus-20240229": (15.00, 75.00),
    "claude-3-sonnet-20240229": (3.00, 15.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    # Default to Gemini Flash rates if model not found
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
