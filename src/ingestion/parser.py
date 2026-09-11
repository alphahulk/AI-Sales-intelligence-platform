"""Convert raw records into stable observation rows."""

import re
import json
import unicodedata
from typing import Any

from src.normalization.domains import normalize_domain, registrable_domain
from src.normalization.services import service_category

LEGAL_SUFFIXES = frozenset({"ag", "bv", "co", "corp", "gmbh", "inc", "llc", "ltd", "plc", "sa"})


def normalize_org(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = re.sub(r"[&+]+", " and ", value)
    words = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE).split()
    while len(words) > 1 and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words) or None


def parse_observation(record: dict[str, Any]) -> dict[str, Any]:
    domains = [normalize_domain(value) for value in record.get("domains", [])]
    hostnames = [normalize_domain(value) for value in record.get("hostnames", [])]
    registrable_domains = {
        registrable
        for normalized_domain in domains
        if normalized_domain and (registrable := registrable_domain(normalized_domain))
    }
    return {
        "ip": record.get("ip_str"),
        "domains": [value for value in domains if value],
        "hostnames": [value for value in hostnames if value],
        "registrable_domains": sorted(registrable_domains),
        "service_category": service_category(record.get("port")),
        "canonical_org": normalize_org(record.get("org")),
        "raw_org": record.get("org"),
        "port": record.get("port"),
        "product": record.get("product"),
        "version": record.get("version"),
        "tags": json.dumps(record.get("tags", []), ensure_ascii=False, sort_keys=True),
        "vulns": json.dumps(record.get("vulns", {}), ensure_ascii=False, sort_keys=True),
        "cpe": json.dumps(record.get("cpe", []), ensure_ascii=False, sort_keys=True),
        "cloud": json.dumps(record.get("cloud"), ensure_ascii=False, sort_keys=True),
        "timestamp": record.get("timestamp"),
        "location": json.dumps(record.get("location"), ensure_ascii=False, sort_keys=True),
        "asn": record.get("asn"),
    }