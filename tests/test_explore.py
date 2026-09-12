from src.workflows.explore import search_accounts


def test_explore_search_prefers_signal_keywords() -> None:
    accounts = [
        {"domain": "quiet.test", "opportunity_score": 90, "critical_vulnerability_observations": 0, "exposed_database_count": 0, "exposed_remote_access_count": 0, "eol_observation_count": 0, "cloud_observation_count": 0, "countries": []},
        {"domain": "db-open.test", "opportunity_score": 60, "critical_vulnerability_observations": 0, "exposed_database_count": 2, "exposed_remote_access_count": 0, "eol_observation_count": 0, "cloud_observation_count": 0, "countries": ["US"]},
        {"domain": "shop.example.com", "opportunity_score": 70, "critical_vulnerability_observations": 1, "exposed_database_count": 0, "exposed_remote_access_count": 0, "eol_observation_count": 0, "cloud_observation_count": 0, "countries": []},
    ]
    databases = search_accounts("exposed mysql database", accounts)
    assert databases[0]["domain"] == "db-open.test"
    named = search_accounts("example.com", accounts)
    assert named[0]["domain"] == "shop.example.com"
