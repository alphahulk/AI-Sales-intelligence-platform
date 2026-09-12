"""Provider manager with automatic fallback support."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.ai.base_provider import BaseProvider, Completion, ProviderError

if TYPE_CHECKING:
    from src.ai.base_provider import Completion


class ProviderManager:
    """Manages multiple AI providers with automatic fallback."""

    def __init__(self, fallback_order: list[str] | None = None):
        self._fallback_order = fallback_order or self._parse_fallback_order()
        self._providers: dict[str, BaseProvider] = {}
        self._active_provider: str | None = None
        self._initialize_providers()

    def _parse_fallback_order(self) -> list[str]:
        order_str = os.getenv("AI_FALLBACK_ORDER", "gemini,claude")
        return [p.strip() for p in order_str.split(",") if p.strip()]

    def _initialize_providers(self):
        for provider_name in self._fallback_order:
            try:
                # Handle aliases
                normalized_name = provider_name.lower()
                if normalized_name in ("google", "gemini"):
                    from src.ai.gemini_provider import GeminiProvider as GeminiProviderClass
                    provider = GeminiProviderClass()
                    normalized_name = "gemini"  # Normalize to gemini
                elif normalized_name == "claude":
                    from src.ai.claude_provider import ClaudeProvider as ClaudeProviderClass
                    provider = ClaudeProviderClass()
                else:
                    print(f"Unknown provider: {provider_name}, skipping", flush=True)
                    continue

                if provider.configured():
                    self._providers[normalized_name] = provider
                    if self._active_provider is None:
                        self._active_provider = normalized_name
                else:
                    print(f"Provider {provider_name} not configured, skipping", flush=True)
            except Exception as error:
                print(f"Failed to initialize {provider_name}: {error}", flush=True)

    def complete(self, prompt: str, *, temperature: float = 0.2) -> Completion:
        """Try providers in fallback order until one succeeds."""
        if not self._providers:
            raise ProviderError(
                "No AI providers configured. Set AI_API_KEY, GOOGLE_API_KEY, or CLAUDE_API_KEY in .env."
            )

        last_error = None
        for provider_name in self._fallback_order:
            if provider_name not in self._providers:
                continue

            provider = self._providers[provider_name]
            try:
                result = provider.complete(prompt, temperature=temperature)
                self._active_provider = provider_name
                return result
            except ProviderError as error:
                last_error = error
                print(f"{provider_name} failed: {error}, trying next provider", flush=True)
                continue

        raise ProviderError(
            f"All providers failed. Last error: {last_error}"
        ) from last_error

    def configured(self) -> bool:
        return len(self._providers) > 0

    def model_name(self) -> str:
        if self._active_provider and self._active_provider in self._providers:
            return self._providers[self._active_provider].model_name()
        return "unknown"

    def provider_name(self) -> str:
        return self._active_provider or "none"

    def get_active_provider(self) -> str:
        return self._active_provider or "none"

    def get_available_providers(self) -> list[str]:
        return list(self._providers.keys())
