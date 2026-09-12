import json
from pathlib import Path

from src.ai.tracing import append_trace, estimate_cost_usd
from src.workflows.audit import build_audit_input, build_prompt
from src.workflows.meeting import build_meeting_context
from src.workflows.outreach import build_outreach_context


def test_audit_input_stays_within_supplied_evidence() -> None:
    evidence = build_audit_input(
        {
            "domain": "example.com",
            "opportunity_score": 71.2,
            "exposure_score": 60,
            "vulnerability_score": 80,
            "technology_score": 40,
            "recency_score": 50,
            "unique_ip_count": 3,
            "score_reasons": '["1 critical vulnerability observations"]',
        },
        [{"signal_type": "vulnerability", "signal_name": "CVE-1", "severity": "critical", "description": "KEV", "confidence": 0.9}],
    )
    assert evidence["domain"] == "example.com"
    assert evidence["signals"][0]["name"] == "CVE-1"
    assert "Do not invent company identity" in evidence["constraints"][0]


def test_audit_prompt_includes_versioned_instructions(tmp_path: Path) -> None:
    prompt = build_prompt({"domain": "example.com", "scores": {"opportunity": 70}})
    assert "Do not invent company facts" in prompt
    assert "example.com" in prompt


def test_trace_schema_and_cost(tmp_path: Path) -> None:
    path = tmp_path / "llm.jsonl"
    append_trace(
        {
            "workflow": "prospect_audit",
            "prompt_version": "audit/v2",
            "model": "gemini-3.6-flash",
            "domain": "example.com",
            "request": "prompt",
            "response": "audit",
            "latency_ms": 120,
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost_usd": estimate_cost_usd("gemini-3.6-flash", 1000, 500),
            "cached": False,
            "error": None,
            "decision": "audit_generated",
        },
        path=path,
    )
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["workflow"] == "prospect_audit"
    assert row["prompt_version"] == "audit/v2"
    assert "timestamp" in row
    assert row["cost_usd"] == 0.00045


def test_meeting_and_outreach_share_account_evidence() -> None:
    account = {"domain": "example.com", "opportunity_score": 71.2}
    signals = [{"signal_type": "vulnerability", "signal_name": "CVE-1", "severity": "critical", "description": "KEV", "confidence": 0.9}]
    meeting = build_meeting_context(account, signals)
    outreach = build_outreach_context(account, signals)
    assert meeting["workflow"] == "meeting_prep"
    assert outreach["workflow"] == "outreach"
    assert meeting["signals"][0]["name"] == "CVE-1"
