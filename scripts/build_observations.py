"""Build partitioned curated observation Parquet from compressed NDJSON."""

import argparse
import hashlib
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.reader import read_records
from src.ingestion.parser import parse_observation
from src.normalization.technologies import detected_technologies

SERVICE_DETECTORS = {
    "ftp", "ssh", "telnet", "smb", "mqtt", "redis", "mysql", "vnc", "ntp", "snmp", "dns"
}
REMOTE_ACCESS_SERVICES = {"ssh", "telnet", "vnc", "rdp_encryption", "pptp"}
DATABASE_SERVICES = {"redis", "mysql", "mongodb", "mssql_ssrp", "influxdb", "clickhouse", "neo4j_browser"}


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_row(record: dict[str, Any], sequence: int) -> dict[str, Any]:
    base = parse_observation(record)
    http = record.get("http") if isinstance(record.get("http"), dict) else {}
    ssl = record.get("ssl") if isinstance(record.get("ssl"), dict) else {}
    vulns = record.get("vulns") if isinstance(record.get("vulns"), dict) else {}
    tags = [str(tag) for tag in as_list(record.get("tags"))]
    technologies = detected_technologies(record)
    services = sorted(set(technologies) & SERVICE_DETECTORS)
    vulnerability_details = [detail for detail in vulns.values() if isinstance(detail, dict)]
    cvss_values = [
        float(detail[key])
        for detail in vulnerability_details
        for key in ("cvss", "cvss_v3", "cvss_v2")
        if isinstance(detail.get(key), (int, float))
    ]
    observation_id = hashlib.sha1(f"{sequence}:{record.get('ip_str')}:{record.get('timestamp')}:{record.get('port')}".encode()).hexdigest()
    return {
        "observation_id": observation_id,
        "timestamp": record.get("timestamp"),
        "ip": record.get("ip_str"),
        "ip_str": record.get("ip_str"),
        "ipv6": record.get("ipv6"),
        "asn": str(record.get("asn")) if record.get("asn") is not None else None,
        "domain": base["domains"][0] if base["domains"] else None,
        "domains": base["domains"],
        "hostname": base["hostnames"][0] if base["hostnames"] else None,
        "hostnames": base["hostnames"],
        "registrable_domains": base["registrable_domains"],
        "country_code": record.get("location", {}).get("country_code") if isinstance(record.get("location"), dict) else None,
        "country_name": record.get("location", {}).get("country_name") if isinstance(record.get("location"), dict) else None,
        "region_code": record.get("location", {}).get("region_code") if isinstance(record.get("location"), dict) else None,
        "city": record.get("location", {}).get("city") if isinstance(record.get("location"), dict) else None,
        "latitude": record.get("location", {}).get("latitude") if isinstance(record.get("location"), dict) else None,
        "longitude": record.get("location", {}).get("longitude") if isinstance(record.get("location"), dict) else None,
        "port": record.get("port"),
        "transport": record.get("transport"),
        "service_category": base["service_category"],
        "product": record.get("product"),
        "version": record.get("version"),
        "os": record.get("os"),
        "http_status": http.get("status"),
        "http_title": http.get("title"),
        "http_server": http.get("server"),
        "http_host": http.get("host"),
        "http_redirect_count": len(http.get("redirects") or []) if isinstance(http.get("redirects"), list) else 0,
        "http_securitytxt": bool(http.get("securitytxt")),
        "http_has_html": bool(http.get("html")),
        "ssl_present": bool(record.get("ssl")),
        "ssl_version": ssl.get("version"),
        "ssl_cert_subject": ssl.get("cert_subject") or ssl.get("subject"),
        "ssl_cert_issuer": ssl.get("cert_issuer") or ssl.get("issuer"),
        "ssl_cert_expiry": ssl.get("cert_expiry") or ssl.get("expires"),
        "cloud_present": bool(record.get("cloud")),
        "cloud_provider": record.get("cloud", {}).get("provider") if isinstance(record.get("cloud"), dict) else None,
        "cloud_region": record.get("cloud", {}).get("region") if isinstance(record.get("cloud"), dict) else None,
        "cloud_service": record.get("cloud", {}).get("service") if isinstance(record.get("cloud"), dict) else None,
        "org": record.get("org"),
        "canonical_org": base["canonical_org"],
        "isp": record.get("isp"),
        "tags": tags,
        "tag_count": len(tags),
        "has_eol_tag": "eol-product" in tags or "eol-os" in tags,
        "cpe": as_list(record.get("cpe")),
        "cpe23": as_list(record.get("cpe23")),
        "cpe_count": len(as_list(record.get("cpe"))),
        "cpe23_count": len(as_list(record.get("cpe23"))),
        "vuln_present": bool(vulns),
        "vuln_count": len(vulns),
        "vuln_ids": sorted(str(vulnerability_id) for vulnerability_id in vulns),
        "vuln_max_cvss": max(cvss_values, default=None),
        "vuln_has_known_exploit": any(bool(detail.get("kev") or detail.get("verified")) for detail in vulnerability_details),
        "detected_technologies": technologies,
        "detected_services": services,
        "service_count": len(services),
        "sensitive_service_count": len(set(services) & (DATABASE_SERVICES | REMOTE_ACCESS_SERVICES)),
        "remote_access_service_count": len(set(services) & REMOTE_ACCESS_SERVICES),
        "database_service_count": len(set(services) & DATABASE_SERVICES),
        "raw_tags_json": json_text(record.get("tags")),
        "raw_vulns_json": json_text(record.get("vulns")),
        "raw_http_json": json_text(record.get("http")),
        "raw_ssl_json": json_text(record.get("ssl")),
    }


def write_part(rows: list[dict[str, Any]], output: Path, part_number: int) -> int:
    table = pa.Table.from_pylist(rows)
    path = output / f"part-{part_number:05d}.parquet"
    pq.write_table(table, path, compression="zstd")
    return len(rows)


def build_observations(source: Path, output: Path, batch_size: int) -> int:
    output.mkdir(parents=True, exist_ok=True)
    total = 0
    part_number = 0
    rows: list[dict[str, Any]] = []
    for sequence, record in enumerate(read_records(source)):
        rows.append(build_row(record, sequence))
        if len(rows) >= batch_size:
            total += write_part(rows, output, part_number)
            rows.clear()
            part_number += 1
    if rows:
        total += write_part(rows, output, part_number)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--batch-size", type=int, default=50_000)
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than zero")
    count = build_observations(args.input, args.output, args.batch_size)
    print(f"Wrote {count:,} observations to {args.output}")


if __name__ == "__main__":
    main()
