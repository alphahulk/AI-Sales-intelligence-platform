"""Gemini (Google AI Studio) completions for account workflows."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_MODEL = "gemini-3.6-flash"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@dataclass
class Completion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cached: bool = False


class ProviderError(RuntimeError):
    pass


def api_key() -> str:
    return (os.getenv("AI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()


def configured() -> bool:
    return bool(api_key())


def model_name() -> str:
    return (os.getenv("AI_MODEL") or DEFAULT_MODEL).strip()


def complete(prompt: str, *, temperature: float = 0.2) -> Completion:
    key = api_key()
    if not key:
        raise ProviderError(
            "No Google AI Studio key found. Set AI_API_KEY or GOOGLE_API_KEY in .env."
        )
    model = model_name()
    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        GEMINI_ENDPOINT.format(model=model) + f"?key={key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(detail).get("error", {}).get("message", detail)
        except json.JSONDecodeError:
            message = detail or str(error)
        raise ProviderError(f"Gemini request failed ({error.code}): {message}") from error
    except urllib.error.URLError as error:
        raise ProviderError(f"Could not reach Gemini: {error.reason}") from error
    latency_ms = int((time.perf_counter() - started) * 1000)
    text = _response_text(body)
    usage = body.get("usageMetadata") or {}
    return Completion(
        text=text,
        model=model,
        input_tokens=int(usage.get("promptTokenCount") or 0),
        output_tokens=int(usage.get("candidatesTokenCount") or 0),
        latency_ms=latency_ms,
    )


def _response_text(body: dict) -> str:
    candidates = body.get("candidates") or []
    if not candidates:
        raise ProviderError(body.get("error", {}).get("message") or "Gemini returned no candidates.")
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    text = "".join(str(part.get("text") or "") for part in parts).strip()
    if not text:
        raise ProviderError("Gemini returned an empty response.")
    return text
