"""Deterministic qualification workflow."""


def qualify(account: dict) -> bool:
    return account.get("opportunity_score", 0) >= 60