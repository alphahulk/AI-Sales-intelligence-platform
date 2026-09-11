"""Domain normalization helpers."""

import re

import tldextract


def normalize_domain(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    domain = value.casefold().strip().rstrip(".")
    return domain.removeprefix("www.") or None


def registrable_domain(value: object) -> str | None:
    domain = normalize_domain(value)
    if not domain or re.fullmatch(r"\d+(?:\.\d+){3}", domain):
        return None
    extracted = tldextract.extract(domain)
    if not extracted.domain or not extracted.suffix:
        return None
    return f"{extracted.domain}.{extracted.suffix}"