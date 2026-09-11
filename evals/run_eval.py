"""Minimal evaluation harness for workflow contracts."""

import json
from pathlib import Path


def main() -> None:
    dataset = Path(__file__).parent / "datasets" / "prospect_audit.jsonl"
    cases = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    print(f"Loaded {len(cases)} evaluation cases")


if __name__ == "__main__":
    main()