from evals.judge import aggregate, score_output


def test_judge_precision_recall() -> None:
    expected = {
        "must_mention": ["CVE-2024-4577", "critical"],
        "must_not_mention": ["500 employees", "CISO Jane"],
    }
    good = score_output("CVE-2024-4577 is critical on the observed host.", expected)
    bad = score_output("CISO Jane said 500 employees were breached.", expected)
    assert good["passed"] is True
    assert good["recall"] == 1
    assert bad["passed"] is False
    assert "CISO Jane" in bad["false_positives"]
    summary = aggregate([good, bad])
    assert summary["cases"] == 2
    assert 0 < summary["precision"] <= 1
