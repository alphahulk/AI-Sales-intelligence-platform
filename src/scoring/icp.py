"""Ideal customer profile scoring."""


def icp_score(account: dict, target_industries: set[str] | None = None) -> float:
    target_industries = target_industries or set()
    industry = account.get("industry")
    return 100.0 if industry in target_industries else 0.0