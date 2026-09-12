"""Claude (Anthropic) provider implementation."""

from __future__ import annotations

import os
import time

from src.ai.base_provider import BaseProvider, Completion, ProviderError

DEFAULT_MODEL = "claude-3-5-haiku-20241022"


class ClaudeProvider(BaseProvider):
    """Anthropic Claude AI provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        try:
            import anthropic
        except ImportError:
            raise ProviderError("Anthropic SDK not installed. Install with: pip install anthropic")
        self._anthropic = anthropic
        self._api_key = api_key or (os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
        # Use Claude-specific model if AI_MODEL is set to a Gemini model
        env_model = model or os.getenv("AI_MODEL") or DEFAULT_MODEL
        if env_model.startswith("gemini"):
            self._model = DEFAULT_MODEL  # Use default Claude model if Gemini model is specified
        else:
            self._model = env_model.strip()
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise ProviderError(
                    "No Anthropic API key found. Set CLAUDE_API_KEY or ANTHROPIC_API_KEY in .env."
                )
            self._client = self._anthropic.Anthropic(
                api_key=self._api_key,
                timeout=120.0,  # Set default timeout
            )
        return self._client

    def complete(self, prompt: str, *, temperature: float = 0.2) -> Completion:
        client = self._get_client()
        started = time.perf_counter()
        try:
            # Claude API - check if temperature is supported
            try:
                response = client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
            except TypeError:
                # Fallback for older Anthropic SDK versions that don't support temperature
                response = client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )
        except Exception as error:
            # Handle various Anthropic exceptions
            error_type = type(error).__name__
            if "APIError" in error_type or "APIConnectionError" in error_type:
                raise ProviderError(f"Claude API error: {error}") from error
            elif "Timeout" in error_type:
                raise ProviderError(f"Claude API timeout: {error}") from error
            elif "RateLimit" in error_type:
                raise ProviderError(f"Claude rate limit exceeded: {error}") from error
            elif "Authentication" in error_type or "Permission" in error_type:
                raise ProviderError(f"Claude authentication failed: {error}") from error
            else:
                raise ProviderError(f"Claude request failed: {error}") from error

        latency_ms = int((time.perf_counter() - started) * 1000)

        # Extract text from response
        text = ""
        if response.content and len(response.content) > 0:
            text = response.content[0].text
        else:
            raise ProviderError("Claude returned an empty response.")

        # Extract usage information
        input_tokens = response.usage.input_tokens if response.usage else 0
        output_tokens = response.usage.output_tokens if response.usage else 0

        return Completion(
            text=text,
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            provider=self.provider_name(),
        )

    def configured(self) -> bool:
        return bool(self._api_key)

    def model_name(self) -> str:
        return self._model

    def provider_name(self) -> str:
        return "claude"
