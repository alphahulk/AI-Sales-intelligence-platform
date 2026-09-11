"""Profile important fields in a Zstandard-compressed NDJSON dataset."""

import argparse
import io
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import unicodedata

import zstandard as zstd

IMPORTANT_FIELDS = (
    "org",
    "domains",
    "hostnames",
    "ip_str",
    "port",
    "product",
    "version",
    "tags",
    "vulns",
    "cpe",
    "cloud",
    "timestamp",
    "location",
    "asn",
)

LEGAL_SUFFIXES = frozenset(
    {
        "ag",
        "ag co",
        "bv",
        "co",
        "company",
        "corp",
        "corporation",
        "gmbh",
        "inc",
        "incorporated",
        "limited",
        "llc",
        "ltd",
        "plc",
        "sa",
    }
)


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def display_value(value: Any, limit: int = 120) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return rendered if len(rendered) <= limit else f"{rendered[:limit - 3]}..."


def canonicalize_org(value: Any) -> str | None:
    """Create a stable organization key without changing the source value."""
    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = re.sub(r"[&+]+", " and ", normalized)
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    words = normalized.split()
    while len(words) > 1 and " ".join(words[-2:]) in LEGAL_SUFFIXES:
        words[-2:] = []
    while len(words) > 1 and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words) or None


def track_value(counter: Counter[str], value: str, capacity: int) -> None:
    """Keep a bounded set of frequent-value candidates."""
    counter[value] += 1
    if len(counter) <= capacity:
        return
    least_common_value, _ = counter.most_common()[-1]
    del counter[least_common_value]


def profile(path: Path, top_values: int) -> dict[str, Any]:
    present: Counter[str] = Counter()
    type_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    value_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    raw_org_counts: Counter[str] = Counter()
    canonical_org_counts: Counter[str] = Counter()
    org_aliases: defaultdict[str, Counter[str]] = defaultdict(Counter)
    candidate_capacity = max(100, top_values * 20)
    record_count = 0
    invalid_lines = 0
    started = time.perf_counter()

    with path.open("rb") as compressed:
        with zstd.ZstdDecompressor().stream_reader(compressed) as decompressed:
            text_stream = io.TextIOWrapper(decompressed, encoding="utf-8")
            for line in text_stream:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    invalid_lines += 1
                    continue
                if not isinstance(record, dict):
                    invalid_lines += 1
                    continue

                record_count += 1
                if "org" in record:
                    raw_org = record["org"]
                    raw_org_display = display_value(raw_org)
                    raw_org_counts[raw_org_display] += 1
                    canonical_org = canonicalize_org(raw_org)
                    if canonical_org is not None:
                        canonical_org_counts[canonical_org] += 1
                        track_value(org_aliases[canonical_org], raw_org_display, candidate_capacity)
                for field in IMPORTANT_FIELDS:
                    if field not in record:
                        continue
                    value = record[field]
                    present[field] += 1
                    type_counts[field][value_type(value)] += 1
                    track_value(value_counts[field], display_value(value), candidate_capacity)

    elapsed = time.perf_counter() - started
    fields = {}
    for field in IMPORTANT_FIELDS:
        fields[field] = {
            "present": present[field],
            "missing": record_count - present[field],
            "types": dict(type_counts[field].most_common()),
            "top_values": value_counts[field].most_common(top_values),
        }

    return {
        "file": str(path),
        "records": record_count,
        "invalid_lines": invalid_lines,
        "elapsed_seconds": round(elapsed, 3),
        "records_per_second": round(record_count / elapsed, 1) if elapsed else None,
        "fields": fields,
        "organization_canonicalization": {
            "raw_unique": len(raw_org_counts),
            "canonical_unique": len(canonical_org_counts),
            "merged_records": sum(
                count for canonical, count in canonical_org_counts.items()
                if len(org_aliases[canonical]) > 1
            ),
            "top_canonical": [
                {
                    "canonical": canonical,
                    "records": count,
                    "aliases": [alias for alias, _ in org_aliases[canonical].most_common()],
                }
                for canonical, count in canonical_org_counts.most_common(top_values)
            ],
        },
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"File: {report['file']}")
    print(f"Records: {report['records']:,}")
    print(f"Invalid/non-object lines: {report['invalid_lines']:,}")
    print(f"Elapsed: {report['elapsed_seconds']:.3f} seconds")
    print(f"Records/sec: {report['records_per_second']:,.1f}")
    organization = report["organization_canonicalization"]
    print(
        "Organizations: "
        f"raw_unique={organization['raw_unique']:,}, "
        f"canonical_unique={organization['canonical_unique']:,}, "
        f"merged_records={organization['merged_records']:,}"
    )
    for item in organization["top_canonical"]:
        aliases = ", ".join(item["aliases"])
        print(f"  {item['canonical']}: {item['records']:,} records; aliases: {aliases}")
    print("\nImportant fields:")
    for field, details in report["fields"].items():
        types = ", ".join(f"{kind}={count:,}" for kind, count in details["types"].items())
        print(
            f"- {field}: present={details['present']:,}, "
            f"missing={details['missing']:,}, types={types or 'none'}"
        )
        if details["top_values"]:
            top = ", ".join(f"{value} ({count:,})" for value, count in details["top_values"])
            print(f"  top values: {top}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="Zstandard-compressed NDJSON file")
    parser.add_argument("--top", type=int, default=5, help="top values per field (default: 5)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="write JSON instead of text")
    args = parser.parse_args()
    if args.top < 0:
        parser.error("--top must be zero or greater")

    report = profile(args.file, args.top)
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
