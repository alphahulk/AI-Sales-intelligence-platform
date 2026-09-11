"""Combine deterministic account signals into an opportunity score."""


def opportunity_score(signals: dict[str, float]) -> float:
    weights = {"icp": 0.30, "exposure": 0.20, "vulnerability": 0.20, "technology": 0.20, "recency": 0.10}
    return min(100.0, sum(weights[key] * float(signals.get(key, 0.0)) for key in weights))