"""Prospect audit workflow: deterministic evidence in, Gemini narrative out."""

from pathlib import Path

from src.ai.generate import GenerationResult, build_account_evidence, compose_prompt, run_generation

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "audit" / "v2.md"
PROMPT_VERSION = "audit/v2"
WORKFLOW = "prospect_audit"

AuditResult = GenerationResult


def build_audit_input(account: dict, signals: list[dict] | None = None) -> dict:
    return build_account_evidence(account, signals, WORKFLOW)


def build_prompt(evidence: dict) -> str:
    return compose_prompt(PROMPT_PATH, evidence)


def run_prospect_audit(account: dict, signals: list[dict] | None = None) -> GenerationResult:
    return run_generation(
        workflow=WORKFLOW,
        prompt_path=PROMPT_PATH,
        prompt_version=PROMPT_VERSION,
        evidence=build_audit_input(account, signals),
        account=account,
    )
