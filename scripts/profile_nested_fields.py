"""Deep-profile nested fields using a reservoir sample of NDJSON records."""

import argparse
import io
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import orjson
import zstandard as zstd

SAMPLE_SIZE = 8_000
NESTED_FIELDS = ("vulns", "ssl", "http", "cloud", "cpe23", "tags", "location", "_shodan")
TECH_DETECTOR_CANDIDATES = (
    "fortinet", "hikvision", "mongodb", "redis", "kubernetes", "mysql",
    "mikrotik_routeros", "sonicwall", "docker_registry", "cisco_anyconnect",
    "synology_dsm", "microsoft_exchange", "elastic", "mqtt", "vnc", "smb",
    "ftp", "ssh", "telnet", "rdp_encryption", "snmp", "ntp", "dns",
    "afp", "airplay", "amqp", "bacnet", "bgp", "bitcoin", "checkpoint",
    "chroma", "chromecast", "cisco_ipsla", "clickhouse", "coap", "codesys",
    "comfyui", "consul", "couchdb", "dahua", "dahua_dvr_web", "dav", "dd_wrt",
    "digi", "docker_registry", "dogecoin_node", "domoticz", "draytek_vigor",
    "elastic", "epmd", "etcd", "ethereum_p2p", "ethereum_rpc", "ethernetip",
    "fast_reverse_proxy", "flink", "ftp", "ganglia", "gemini", "gl_inet", "h323",
    "hbase", "hermes_agent", "home_assistant", "homebridge", "homematic_ccu",
    "hp_ilo", "hp_printer_embedded_web_server", "huawei_home_gateway", "ibm_db2",
    "influxdb", "ip_camera", "ip_symcon", "ipmi", "ipp_cups", "isakmp", "iscsi",
    "knx", "lantronix", "ldap", "litecoin_node", "llama_cpp", "lm_studio", "localai",
    "mcp", "mdns", "microsoft_exchange", "mikrotik_winbox", "milesight_routers", "milvus",
    "minecraft", "mitsubishi_q", "monero", "mqtt", "msrpc", "mssql_ssrp", "mysqlx",
    "nats", "ndmp", "neo4j_browser", "netbios", "netdata", "netgear", "netusb", "nmea",
    "node_exporter", "nsq", "ntlm", "ntp", "ntrip", "ollama", "open_dir", "openflow",
    "openwebnet", "oracle_tnslsnr", "pcworx", "pgbouncer", "philips_hue", "plex", "pptp",
    "qnap", "questdb", "radius", "raspberry_shake", "redis", "riak_http", "rip", "rsync",
    "samsung_syncthru_web_service", "samsung_tv", "seven_days_to_die", "siemens_s7",
    "skywalking", "smb", "sonicwall", "sony_bravia", "spotify_connect", "steam_a2s",
    "steam_ihs", "stun", "superset", "synology_srm", "tacacs", "tasmota", "telnet",
    "tibia", "tidb", "tilginAB_home_gateway", "tp_link_kasa", "tp_link_kasa_new",
    "trane_tracer_sc", "ubiquiti", "unitronics_pcom", "upnp", "vault", "vmware",
    "wince_cerdisp", "windows_exporter", "xiaomi_miio", "zeromq",
)
CLOUD_PTR_PATTERNS = (
    re.compile(r"(^|\.)googleusercontent\.com$", re.IGNORECASE),
    re.compile(r"(^|\.)amazonaws\.com$", re.IGNORECASE),
    re.compile(r"(^|\.)compute\.internal$", re.IGNORECASE),
    re.compile(r"(^|\.)cloudapp\.azure\.com$", re.IGNORECASE),
)


def reservoir_sample(path: Path, sample_size: int, seed: int | None = None) -> tuple[list[bytes], int]:
    random_generator = random.Random(seed)
    reservoir: list[bytes] = []
    record_count = 0
    with path.open("rb") as file_handle, zstd.ZstdDecompressor().stream_reader(file_handle) as reader:
        text_stream = io.TextIOWrapper(reader, encoding="utf-8")
        for line in text_stream:
            if not line.strip():
                continue
            record_count += 1
            if len(reservoir) < sample_size:
                reservoir.append(line.encode("utf-8"))
            else:
                replacement_index = random_generator.randrange(record_count)
                if replacement_index < sample_size:
                    reservoir[replacement_index] = line.encode("utf-8")
    return reservoir, record_count


def parse_records(lines: list[bytes]) -> list[dict[str, Any]]:
    records = []
    for line in lines:
        try:
            record = orjson.loads(line)
        except orjson.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def profile_vulns(records: list[dict[str, Any]]) -> dict[str, Any]:
    structures = Counter()
    detail_keys = Counter()
    cvss_present = 0
    exploit_flag_present = 0
    cve_count = 0
    records_with_vulns = 0
    for record in records:
        vulns = record.get("vulns")
        if not vulns:
            continue
        records_with_vulns += 1
        if not isinstance(vulns, dict):
            structures[type(vulns).__name__] += 1
            continue
        for detail in vulns.values():
            cve_count += 1
            if isinstance(detail, dict):
                structures["dict"] += 1
                detail_keys.update(detail.keys())
                cvss_present += int("cvss" in detail or "cvss_v3" in detail or "cvss_v2" in detail)
                exploit_flag_present += int(
                    any(key in detail for key in ("verified", "kev", "exploit", "exploited"))
                    or "kev" in str(detail).casefold()
                )
            else:
                structures[type(detail).__name__] += 1
    return {
        "records_with_vulns": records_with_vulns,
        "cve_details_seen": cve_count,
        "value_type_distribution": dict(structures),
        "records_with_cvss": cvss_present,
        "records_with_exploit_or_kev_flag": exploit_flag_present,
        "detail_keys_seen": dict(detail_keys.most_common(30)),
    }


def profile_domains_hostnames(records: list[dict[str, Any]]) -> dict[str, Any]:
    domain_counts = Counter(len(record.get("domains") or []) for record in records)
    hostname_counts = Counter(len(record.get("hostnames") or []) for record in records)
    return {
        "domains_per_record_distribution": {str(key): value for key, value in sorted(domain_counts.items())},
        "hostnames_per_record_distribution": {str(key): value for key, value in sorted(hostname_counts.items())},
        "max_domains": max(domain_counts, default=0),
        "max_hostnames": max(hostname_counts, default=0),
    }


def profile_identity(records: list[dict[str, Any]]) -> dict[str, Any]:
    domain_records = 0
    hostname_records = 0
    zero_domain_records = 0
    cloud_ptr_records = 0
    exact_googleusercontent_records = 0
    domain_counter = Counter()
    for record in records:
        domains = [str(value).casefold().rstrip(".") for value in (record.get("domains") or [])]
        hostnames = [str(value).casefold().rstrip(".") for value in (record.get("hostnames") or [])]
        if domains:
            domain_records += 1
            domain_counter.update(domains)
        else:
            zero_domain_records += 1
        hostname_records += int(bool(hostnames))
        identity_values = domains + hostnames
        is_cloud_ptr = any(pattern.search(value) for value in identity_values for pattern in CLOUD_PTR_PATTERNS)
        cloud_ptr_records += int(is_cloud_ptr)
        exact_googleusercontent_records += int(domains == ["googleusercontent.com"])
    return {
        "records_with_domains": domain_records,
        "records_without_domains": zero_domain_records,
        "records_with_hostnames": hostname_records,
        "estimated_domain_coverage": domain_records / len(records) if records else 0,
        "cloud_ptr_pattern_records": cloud_ptr_records,
        "exact_googleusercontent_domain_records": exact_googleusercontent_records,
        "top_domains_in_sample": dict(domain_counter.most_common(30)),
    }


def profile_tags(records: list[dict[str, Any]]) -> dict[str, int]:
    counter = Counter()
    for record in records:
        counter.update(record.get("tags") or [])
    return dict(counter.most_common(100))


def profile_technologies(records: list[dict[str, Any]]) -> dict[str, Any]:
    presence = Counter()
    cooccurrences = Counter()
    examples = []
    for record in records:
        detected = sorted({key for key in TECH_DETECTOR_CANDIDATES if record.get(key) is not None})
        presence.update(detected)
        for left_index, left in enumerate(detected):
            for right in detected[left_index + 1:]:
                cooccurrences[f"{left}+{right}"] += 1
        if len(detected) > 1 and len(examples) < 20:
            examples.append(detected)
    return {
        "candidate_count": len(TECH_DETECTOR_CANDIDATES),
        "presence_counts": dict(presence.most_common()),
        "above_100_occurrences": {key: value for key, value in presence.items() if value > 100},
        "cooccurrence_counts": dict(cooccurrences.most_common(50)),
        "multi_technology_examples": examples,
    }


def profile_nested_structure(records: list[dict[str, Any]], field: str) -> dict[str, Any]:
    value_types = Counter()
    keys = Counter()
    present = 0
    for record in records:
        value = record.get(field)
        if value is None:
            continue
        present += 1
        value_types[type(value).__name__] += 1
        if isinstance(value, dict):
            keys.update(value.keys())
    return {"present": present, "value_types": dict(value_types), "keys": dict(keys.most_common(50))}


def profile_ports_orgs(records: list[dict[str, Any]]) -> dict[str, Any]:
    ports = Counter(record.get("port") for record in records if record.get("port") is not None)
    organizations = Counter(record.get("org") for record in records if record.get("org"))
    products = Counter(record.get("product") for record in records if record.get("product"))
    return {
        "ports_top100": {str(port): count for port, count in ports.most_common(100)},
        "organizations_top100": {str(org): count for org, count in organizations.most_common(100)},
        "products_top100": {str(product): count for product, count in products.most_common(100)},
    }


def build_report(records: list[dict[str, Any]], total_records: int, sample_size: int) -> dict[str, Any]:
    nested = {field: profile_nested_structure(records, field) for field in NESTED_FIELDS}
    ports_orgs = profile_ports_orgs(records)
    vulnerabilities = profile_vulns(records)
    report = {
        "sample_size": sample_size,
        "total_records_streamed": total_records,
        "sampling": "uniform reservoir sample",
        "vulns": vulnerabilities,
        "domains_hostnames": profile_domains_hostnames(records),
        "identity_resolution": profile_identity(records),
        "tags_top100": profile_tags(records),
        "technologies": profile_technologies(records),
        "ports": ports_orgs["ports_top100"],
        "organizations": ports_orgs["organizations_top100"],
        "products": ports_orgs["products_top100"],
        "nested_fields": nested,
        "ssl": nested["ssl"],
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.sample_size <= 0:
        parser.error("--sample-size must be greater than zero")
    lines, total_records = reservoir_sample(args.input, args.sample_size, args.seed)
    records = parse_records(lines)
    report = build_report(records, total_records, len(records))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(orjson.dumps(report, option=orjson.OPT_INDENT_2))
    sibling_reports = {
        "dataset_profile.json": {
            "sample_size": len(records),
            "total_records_streamed": total_records,
            "sampling": report["sampling"],
        },
        "tags_distribution.json": {"sample_size": len(records), "tags_top100": report["tags_top100"]},
        "technologies_distribution.json": {"sample_size": len(records), "technologies": report["technologies"]},
        "ports_distribution.json": {"sample_size": len(records), "ports_top100": report["ports"]},
        "organizations_distribution.json": {
            "sample_size": len(records),
            "organizations_top100": report["organizations"],
        },
        "products_distribution.json": {
            "sample_size": len(records),
            "products_top100": report["products"],
        },
        "vulnerabilities_distribution.json": {
            "sample_size": len(records),
            "vulns": report["vulns"],
        },
    }
    for filename, content in sibling_reports.items():
        (args.output.parent / filename).write_bytes(orjson.dumps(content, option=orjson.OPT_INDENT_2))
    print(f"Profiled {len(records):,} random records from {total_records:,} total records")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()