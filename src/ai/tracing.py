"""Tracing boundary for future provider calls."""

from contextlib import contextmanager
from collections.abc import Iterator


@contextmanager
def trace(name: str) -> Iterator[None]:
    yield