"""Deterministic signal extraction from normalized observations."""


def signal_counts(row: dict) -> dict[str, float]:
    return {
        "exposure": float(bool(row.get("port"))),
        "vulnerability": float(bool(row.get("vulns"))),
        "technology": float(bool(row.get("product") or row.get("cpe"))),
    }