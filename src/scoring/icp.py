"""Technical ICP proxy. Firmographic industry/size are not in the source dataset."""


def icp_score(account: dict, target_industries: set[str] | None = None) -> float:
    target_industries = target_industries or set()
    industry = account.get("industry")
    if industry and target_industries:
        return 100.0 if industry in target_industries else 25.0

    ips = int(account.get("unique_ip_count") or 0)
    services = int(account.get("unique_service_count") or 0)
    technologies = [item for item in (account.get("technologies") or []) if not str(item).startswith("_")]
    cloud = int(account.get("cloud_observation_count") or 0)
    countries = account.get("countries") or []

    score = 40.0
    if 3 <= ips <= 200:
        score += 20.0
    elif ips > 200:
        score += 8.0
    if services >= 3:
        score += 15.0
    if len(technologies) >= 2:
        score += 15.0
    if countries:
        score += 10.0
    if cloud and ips >= 10 and services <= 2 and len(technologies) <= 1:
        score -= 15.0
    return round(max(0.0, min(100.0, score)), 2)
