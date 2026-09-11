"""Technology detector normalization."""

NON_TECHNOLOGY_FIELDS = {
    "data", "opts", "port", "transport", "timestamp", "domains", "hostnames", "location",
    "org", "isp", "asn", "ip", "ip_str", "ipv6", "hash", "product", "version", "os",
    "http", "ssl", "cloud", "cpe", "cpe23", "cpe23_hash", "tags", "vulns", "info",
    "screenshot", "title", "device", "devicetype", "platform", "vendor", "uptime", "_shodan",
}

def detected_technologies(record: dict) -> list[str]:
    return sorted(
        key for key, value in record.items()
        if value is not None
        and key not in NON_TECHNOLOGY_FIELDS
        and not key.startswith("_")
        and isinstance(value, (dict, list, str, int, float, bool))
    )