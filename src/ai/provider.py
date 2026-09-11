"""Provider interface kept separate from deterministic analytics."""

from typing import Protocol


class Provider(Protocol):
    def complete(self, prompt: str) -> str: ...