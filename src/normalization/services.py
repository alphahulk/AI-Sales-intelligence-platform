"""Service and service-category normalization."""

SERVICE_CATEGORIES = {
    22: "remote_access",
    23: "remote_access",
    21: "file_transfer",
    25: "mail",
    53: "dns",
    80: "web",
    443: "web",
    3306: "database",
    3389: "remote_access",
    5432: "database",
    6379: "database",
    9200: "database",
}


def service_category(port: object) -> str | None:
    return SERVICE_CATEGORIES.get(port) if isinstance(port, int) else None