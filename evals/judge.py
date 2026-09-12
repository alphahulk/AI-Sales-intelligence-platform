"""Lexical judge for prospect-audit labelled cases."""

from __future__ import annotations


def score_output(text: str, expected: dict) -> dict:
    haystack = (text or "").casefold()
    required = list(expected.get("must_mention") or [])
    forbidden = list(expected.get("must_not_mention") or [])
    true_positives = [item for item in required if item.casefold() in haystack]
    false_negatives = [item for item in required if item.casefold() not in haystack]
    false_positives = [item for item in forbidden if item.casefold() in haystack]
    tp = len(true_positives)
    fn = len(false_negatives)
    fp = len(false_positives)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    passed = fn == 0 and fp == 0 and bool(text.strip())
    return {
        "true_positives": true_positives,
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "passed": passed,
    }


def aggregate(rows: list[dict]) -> dict:
    tp = sum(len(row["true_positives"]) for row in rows)
    fp = sum(len(row["false_positives"]) for row in rows)
    fn = sum(len(row["false_negatives"]) for row in rows)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    pass_rate = sum(1 for row in rows if row["passed"]) / len(rows) if rows else 0.0
    return {
        "cases": len(rows),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "pass_rate": round(pass_rate, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
    }
