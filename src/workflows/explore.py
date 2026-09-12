"""Natural-language account search: rules first, Gemini ranks a shortlist."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.ai.generate import GenerationResult, compose_prompt, run_generation

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "explore" / "v1.md"
PROMPT_VERSION = "explore/v1"
WORKFLOW = "explore"

KEYWORD_FILTERS = (
    (("critical", "cve", "vulnerability", "vuln", "exploit", "kev"), "critical_vulnerability_observations"),
    (("database", "mysql", "postgres", "mongodb", "redis", "elasticsearch", "exposed db"), "exposed_database_count"),
    (("rdp", "ssh", "remote", "vnc", "telnet", "vpn"), "exposed_remote_access_count"),
    (("eol", "end of life", "legacy", "unsupported"), "eol_observation_count"),
    (("cloud", "aws", "azure", "gcp", "amazon"), "cloud_observation_count"),
)


@dataclass
class ExploreResult:
    explanation: str
    domains: list[str]
    generation: GenerationResult | None = None
    error: str | None = None


def compact_row(account: dict) -> dict:
    countries = [str(item) for item in (account.get("countries") or []) if item]
    return {
        "domain": account.get("domain"),
        "opportunity_score": round(float(account.get("opportunity_score") or 0), 1),
        "vulnerability_count": account.get("vulnerability_count") or 0,
        "critical": account.get("critical_vulnerability_observations") or 0,
        "exposed_databases": account.get("exposed_database_count") or 0,
        "remote_access": account.get("exposed_remote_access_count") or 0,
        "eol": account.get("eol_observation_count") or 0,
        "cloud": account.get("cloud_observation_count") or 0,
        "country": countries[0] if countries else None,
    }


def search_accounts(question: str, accounts: list[dict], limit: int = 80) -> list[dict]:
    query = question.strip().casefold()
    if not query:
        return accounts[:limit]
    tokens = [token for token in re.split(r"[^a-z0-9.\-]+", query) if token]
    scored: list[dict] = []
    for account in accounts:
        domain = str(account.get("domain") or "").casefold()
        haystack = domain + " " + " ".join(str(item).casefold() for item in (account.get("countries") or []))
        points = 0
        if query in domain or any(token in domain for token in tokens if "." in token):
            points += 50
        for token in tokens:
            if len(token) >= 3 and token in haystack:
                points += 8
        for keywords, field in KEYWORD_FILTERS:
            if any(keyword in query for keyword in keywords) and (account.get(field) or 0) > 0:
                points += 20
        if points:
            scored.append(account)
    pool = scored or accounts
    return sorted(pool, key=lambda item: (item.get("opportunity_score") or 0), reverse=True)[:limit]


def _parse_payload(text: str, fallback: list[str]) -> tuple[str, list[str]]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return text.strip(), fallback
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return text.strip(), fallback
    domains = [str(item) for item in (payload.get("domains") or []) if item]
    explanation = str(payload.get("explanation") or text.strip())
    return explanation, domains or fallback


def run_explore(question: str, accounts: list[dict]) -> ExploreResult:
    candidates = search_accounts(question, accounts)
    fallback = [str(item.get("domain")) for item in candidates[:15]]
    evidence = {
        "question": question,
        "shortlist": [compact_row(item) for item in candidates[:25]],
        "constraints": ["Only use domains from shortlist", "Do not invent firmographics"],
    }
    generation = run_generation(
        workflow=WORKFLOW,
        prompt_path=PROMPT_PATH,
        prompt_version=PROMPT_VERSION,
        evidence=evidence,
        account={"domain": "explore"},
    )
    if generation.error:
        return ExploreResult(
            explanation="",
            domains=fallback,
            generation=generation,
            error=generation.error,
        )
    explanation, domains = _parse_payload(generation.text, fallback)
    allowed = {str(item.get("domain")) for item in candidates}
    domains = [item for item in domains if item in allowed] or fallback
    return ExploreResult(explanation=explanation, domains=domains, generation=generation)
