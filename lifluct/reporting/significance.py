"""Paired-difference helpers for fair model comparisons."""

from __future__ import annotations

import statistics
from typing import Any, Sequence

from lifluct.reporting.bootstrap import bootstrap_confidence_interval


def paired_metric_differences(
    rows: Sequence[dict[str, Any]],
    *,
    contender_model: str,
    comparator_model: str,
    metric_key: str,
) -> list[float]:
    contenders = {
        _pair_key(row): float(row[metric_key])
        for row in rows
        if str(row.get("model_type", row.get("baseline_type"))) == contender_model
        and row.get(metric_key) is not None
    }
    comparators = {
        _pair_key(row): float(row[metric_key])
        for row in rows
        if str(row.get("model_type", row.get("baseline_type"))) == comparator_model
        and row.get(metric_key) is not None
    }
    keys = sorted(set(contenders).intersection(comparators))
    return [contenders[key] - comparators[key] for key in keys]


def paired_difference_summary(
    rows: Sequence[dict[str, Any]],
    *,
    contender_model: str,
    comparator_model: str,
    metric_key: str,
    bootstrap_seed: int = 7,
) -> dict[str, float | int | str]:
    diffs = paired_metric_differences(
        rows,
        contender_model=contender_model,
        comparator_model=comparator_model,
        metric_key=metric_key,
    )
    if not diffs:
        return {
            "metric": metric_key,
            "contender_model": contender_model,
            "comparator_model": comparator_model,
            "count": 0,
            "mean_diff": 0.0,
            "median_diff": 0.0,
            "win_rate": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
        }
    ci = bootstrap_confidence_interval(diffs, metric="median", seed=bootstrap_seed)
    return {
        "metric": metric_key,
        "contender_model": contender_model,
        "comparator_model": comparator_model,
        "count": len(diffs),
        "mean_diff": statistics.fmean(diffs),
        "median_diff": float(statistics.median(diffs)),
        "win_rate": sum(diff > 0.0 for diff in diffs) / len(diffs),
        "ci_lower": float(ci["lower"]),
        "ci_upper": float(ci["upper"]),
    }


def _pair_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("regime_id"),
        row.get("seed"),
        row.get("evaluation_split"),
    )
