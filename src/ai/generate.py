"""Shared Gemini generation with cache and traces."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from src.ai import cache as ai_cache
from src.ai.provider import Completion, ProviderError, complete, configured, model_name
from src.ai.tracing import append_trace, estimate_cost_usd

_CACHE = ai_cache.MemoryCache()


@dataclass
class GenerationResult:
    text: str
    model: str
    prompt_version: str
    cached: bool
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    error: str | None = None


def build_account_evidence(account: dict, signals: list[dict] | None, workflow: str, limit: int = 20) -> dict:
    reasons = account.get("score_reasons") or []
    if isinstance(reasons, str):
        try:
            reasons = json.loads(reasons)
        except json.JSONDecodeError:
            reasons = [reasons]
    return {
        "workflow": workflow,
        "domain": account.get("domain"),
        "scores": {
            "opportunity": account.get("opportunity_score"),
            "exposure": account.get("exposure_score"),
            "vulnerability": account.get("vulnerability_score"),
            "technology": account.get("technology_score"),
            "recency": account.get("recency_score"),
        },
        "footprint": {
            "unique_ips": account.get("unique_ip_count"),
            "unique_ports": account.get("unique_port_count"),
            "unique_services": account.get("unique_service_count"),
            "cloud_observations": account.get("cloud_observation_count"),
            "exposed_databases": account.get("exposed_database_count"),
            "exposed_remote_access": account.get("exposed_remote_access_count"),
            "eol_observations": account.get("eol_observation_count"),
            "vulnerability_count": account.get("vulnerability_count"),
            "critical_vulnerabilities": account.get("critical_vulnerability_observations"),
            "high_vulnerabilities": account.get("high_vulnerability_observations"),
        },
        "score_reasons": reasons,
        "signals": [
            {
                "type": signal.get("signal_type"),
                "name": signal.get("signal_name"),
                "severity": signal.get("severity"),
                "description": signal.get("description"),
                "confidence": signal.get("confidence"),
            }
            for signal in (signals or [])[:limit]
        ],
        "constraints": [
            "Do not invent company identity, industry, employee count, or contacts.",
            "Treat scores as precomputed. Do not recalculate opportunity_score.",
            "Separate observed facts from hypotheses. Label uncertainty.",
        ],
    }


def compose_prompt(prompt_path: Path, evidence: dict, extra: str = "") -> str:
    instructions = prompt_path.read_text(encoding="utf-8").strip()
    extra_block = f"{extra.strip()}\n\n" if extra.strip() else ""
    return (
        f"{instructions}\n\n"
        f"{extra_block}"
        "Use only the JSON evidence below. If a fact is missing, say it is missing.\n\n"
        f"```json\n{json.dumps(evidence, default=str, indent=2)}\n```"
    )


def run_generation(
    *,
    workflow: str,
    prompt_path: Path,
    prompt_version: str,
    evidence: dict,
    account: dict,
    extra: str = "",
) -> GenerationResult:
    prompt = compose_prompt(prompt_path, evidence, extra)
    model = model_name()
    key = f"{prompt_version}:{hashlib.sha256(f'{model}\n{prompt}'.encode()).hexdigest()}"
    cached_text = _CACHE.get(key)
    if cached_text:
        result = GenerationResult(
            text=cached_text,
            model=model,
            prompt_version=prompt_version,
            cached=True,
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
        )
        _write_trace(workflow, account, prompt, result, None)
        return result

    if not configured():
        result = GenerationResult(
            text="",
            model=model,
            prompt_version=prompt_version,
            cached=False,
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            error="No Google AI Studio key found. Set AI_API_KEY or GOOGLE_API_KEY in .env.",
        )
        _write_trace(workflow, account, prompt, result, result.error)
        return result

    try:
        completion: Completion = complete(prompt)
    except ProviderError as error:
        result = GenerationResult(
            text="",
            model=model,
            prompt_version=prompt_version,
            cached=False,
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            error=str(error),
        )
        _write_trace(workflow, account, prompt, result, result.error)
        return result

    cost = estimate_cost_usd(completion.model, completion.input_tokens, completion.output_tokens)
    _CACHE.set(key, completion.text)
    result = GenerationResult(
        text=completion.text,
        model=completion.model,
        prompt_version=prompt_version,
        cached=False,
        latency_ms=completion.latency_ms,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        cost_usd=cost,
    )
    _write_trace(workflow, account, prompt, result, None)
    return result


def _write_trace(workflow: str, account: dict, prompt: str, result: GenerationResult, error: str | None) -> None:
    append_trace(
        {
            "workflow": workflow,
            "prompt_version": result.prompt_version,
            "model": result.model,
            "domain": account.get("domain"),
            "request": prompt,
            "response": result.text,
            "latency_ms": result.latency_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_usd": result.cost_usd,
            "cached": result.cached,
            "error": error,
            "decision": f"{workflow}_generated" if result.text and not error else f"{workflow}_failed",
        }
    )
