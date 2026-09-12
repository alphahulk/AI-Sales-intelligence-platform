"""Base provider interface for AI providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Completion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cached: bool = False
    provider: str = ""


class ProviderError(RuntimeError):
    pass


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def complete(self, prompt: str, *, temperature: float = 0.2) -> Completion:
        """Generate a completion for the given prompt."""
        pass

    @abstractmethod
    def configured(self) -> bool:
        """Check if the provider is properly configured with API keys."""
        pass

    @abstractmethod
    def model_name(self) -> str:
        """Get the model name to use."""
        pass

    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name (e.g., 'gemini', 'claude')."""
        pass
