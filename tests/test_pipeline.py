from src.ingestion.parser import normalize_domain, normalize_org, parse_observation
from src.scoring.icp import icp_score
from src.scoring.opportunity import opportunity_score
from scripts.build_observations import build_row
from scripts.build_scores import score_account
from datetime import datetime


def test_normalization() -> None:
    assert normalize_org(" Google LLC ") == "google"
    assert normalize_domain("WWW.Example.COM.") == "example.com"


def test_observation_shape() -> None:
    row = parse_observation({"org": "Acme Inc", "domains": ["www.example.com"]})
    assert row["canonical_org"] == "acme"
    assert row["domains"] == ["example.com"]


def test_opportunity_score_is_bounded() -> None:
    assert opportunity_score({"icp": 100, "exposure": 100, "vulnerability": 100, "technology": 100, "recency": 100}) == 100


def test_technical_icp_prefers_org_like_footprints() -> None:
    org_like = icp_score({
        "unique_ip_count": 8,
        "unique_service_count": 4,
        "technologies": ["fortinet", "nginx"],
        "countries": ["US"],
        "cloud_observation_count": 0,
    })
    cdn_like = icp_score({
        "unique_ip_count": 40,
        "unique_service_count": 1,
        "technologies": [],
        "cloud_observation_count": 20,
        "countries": [],
    })
    assert org_like > cdn_like
    assert 0 <= org_like <= 100


def test_curated_observation_extracts_evidence() -> None:
    row = build_row(
        {
            "ip_str": "1.2.3.4",
            "domains": ["app.example.com"],
            "port": 443,
            "http": {"status": 200, "title": "Example"},
            "vulns": {"CVE-1": {"cvss": 9.8, "kev": True}},
            "tags": ["eol-product"],
            "fortinet": {"version": "1"},
        },
        0,
    )
    assert row["registrable_domains"] == ["example.com"]
    assert row["http_status"] == 200
    assert row["vuln_max_cvss"] == 9.8
    assert row["vuln_has_known_exploit"] is True
    assert row["has_eol_tag"] is True


def test_account_score_is_explainable_and_bounded() -> None:
    scored = score_account(
        {
            "account_id": "example.com",
            "unique_port_count": 20,
            "unique_service_count": 4,
            "exposed_database_count": 2,
            "exposed_remote_access_count": 3,
            "critical_vulnerability_observations": 1,
            "high_vulnerability_observations": 2,
            "vulnerability_count": 5,
            "technologies": ["fortinet", "kubernetes"],
            "eol_observation_count": 1,
            "last_seen": datetime(2026, 9, 11),
        },
        datetime(2026, 9, 11),
    )
    assert 0 <= scored["opportunity_score"] <= 100
    assert scored["critical_vulnerability_observations"] == 1
    assert "critical vulnerability" in scored["score_reasons"]
    assert scored["icp_score"] > 50