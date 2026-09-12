"""Gemini (Google AI Studio) provider implementation."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from src.ai.base_provider import BaseProvider, Completion, ProviderError

DEFAULT_MODEL = "gemini-3.6-flash"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider(BaseProvider):
    """Google Gemini AI provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or (os.getenv("AI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        # Use Gemini-specific model if AI_MODEL is set to a Claude model
        env_model = model or os.getenv("AI_MODEL") or DEFAULT_MODEL
        if env_model.startswith("claude"):
            self._model = DEFAULT_MODEL  # Use default Gemini model if Claude model is specified
        else:
            self._model = env_model.strip()

    def complete(self, prompt: str, *, temperature: float = 0.2) -> Completion:
        if not self._api_key:
            raise ProviderError(
                "No Google AI Studio key found. Set AI_API_KEY or GOOGLE_API_KEY in .env."
            )
        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature},
            }
        ).encode("utf-8")
        started = time.perf_counter()
        body = self._post_with_retry(payload)
        latency_ms = int((time.perf_counter() - started) * 1000)
        text = self._response_text(body)
        usage = body.get("usageMetadata") or {}
        return Completion(
            text=text,
            model=self._model,
            input_tokens=int(usage.get("promptTokenCount") or 0),
            output_tokens=int(usage.get("candidatesTokenCount") or 0),
            latency_ms=latency_ms,
            provider=self.provider_name(),
        )

    def configured(self) -> bool:
        return bool(self._api_key)

    def model_name(self) -> str:
        return self._model

    def provider_name(self) -> str:
        return "gemini"

    def _post_with_retry(self, payload: bytes, attempts: int = 6) -> dict:
        last_message = "Gemini request failed"
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(
                GEMINI_ENDPOINT.format(model=self._model) + f"?key={self._api_key}",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                try:
                    last_message = json.loads(detail).get("error", {}).get("message", detail)
                except json.JSONDecodeError:
                    last_message = detail or str(error)
                if error.code == 429 and attempt < attempts:
                    wait = 40 * attempt
                    print(f"Gemini 429, retry {attempt}/{attempts - 1} in {wait}s", flush=True)
                    time.sleep(wait)
                    continue
                raise ProviderError(f"Gemini request failed ({error.code}): {last_message}") from error
            except urllib.error.URLError as error:
                # Handle timeout errors specifically for fallback
                if "timed out" in str(error).lower() or "timeout" in str(error).lower():
                    raise ProviderError(f"Gemini request timed out: {error.reason}") from error
                raise ProviderError(f"Could not reach Gemini: {error.reason}") from error
            except TimeoutError as error:
                raise ProviderError(f"Gemini request timed out: {error}") from error
        raise ProviderError(f"Gemini request failed: {last_message}")

    def _response_text(self, body: dict) -> str:
        candidates = body.get("candidates") or []
        if not candidates:
            raise ProviderError(body.get("error", {}).get("message") or "Gemini returned no candidates.")
        parts = ((candidates[0].get("content") or {}).get("parts")) or []
        text = "".join(str(part.get("text") or "") for part in parts).strip()
        if not text:
            raise ProviderError("Gemini returned an empty response.")
        return text
