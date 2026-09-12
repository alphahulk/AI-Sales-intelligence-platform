"""Meeting preparation workflow."""

from pathlib import Path

from src.ai.generate import GenerationResult, build_account_evidence, run_generation

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "meeting_prep" / "v1.md"
PROMPT_VERSION = "meeting_prep/v1"
WORKFLOW = "meeting_prep"


def build_meeting_context(account: dict, signals: list[dict] | None = None) -> dict:
    return build_account_evidence(account, signals, WORKFLOW)


def run_meeting_prep(account: dict, signals: list[dict] | None = None) -> GenerationResult:
    return run_generation(
        workflow=WORKFLOW,
        prompt_path=PROMPT_PATH,
        prompt_version=PROMPT_VERSION,
        evidence=build_meeting_context(account, signals),
        account=account,
        extra="Output a short meeting brief: objective, evidence-backed talking points, and 5 discovery questions each tied to a named signal.",
    )
