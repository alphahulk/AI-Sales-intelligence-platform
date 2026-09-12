"""Outreach workflow."""

from pathlib import Path

from src.ai.generate import GenerationResult, build_account_evidence, run_generation

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "outreach" / "v1.md"
PROMPT_VERSION = "outreach/v1"
WORKFLOW = "outreach"


def build_outreach_context(account: dict, signals: list[dict] | None = None) -> dict:
    return build_account_evidence(account, signals, WORKFLOW)


def run_outreach_draft(account: dict, signals: list[dict] | None = None) -> GenerationResult:
    return run_generation(
        workflow=WORKFLOW,
        prompt_path=PROMPT_PATH,
        prompt_version=PROMPT_VERSION,
        evidence=build_outreach_context(account, signals),
        account=account,
        extra="Draft one email: subject line plus 80-120 word body. Cite only observed signals. Do not claim a confirmed customer relationship or named contact.",
    )
