"""AI provider completions with multi-provider support and automatic fallback."""

from __future__ import annotations

import os

from src.ai.base_provider import Completion, ProviderError
from src.ai.provider_manager import ProviderManager

# Global provider manager instance
_provider_manager: ProviderManager | None = None


def _get_provider_manager() -> ProviderManager:
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def api_key() -> str:
    """Get API key (legacy compatibility - returns first available key)."""
    return (
        os.getenv("AI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("CLAUDE_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or ""
    ).strip()


def configured() -> bool:
    """Check if any AI provider is configured."""
    return _get_provider_manager().configured()


def model_name() -> str:
    """Get the current model name."""
    return _get_provider_manager().model_name()


def complete(prompt: str, *, temperature: float = 0.2) -> Completion:
    """Generate a completion using available providers with automatic fallback."""
    return _get_provider_manager().complete(prompt, temperature=temperature)


def get_active_provider() -> str:
    """Get the name of the currently active provider."""
    return _get_provider_manager().get_active_provider()


def get_available_providers() -> list[str]:
    """Get list of available/configured providers."""
    return _get_provider_manager().get_available_providers()
