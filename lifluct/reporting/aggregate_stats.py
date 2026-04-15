"""Aggregate statistics for large-scale regime-family experiments."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Sequence

from lifluct.reporting.bootstrap import bootstrap_confidence_interval
from lifluct.reporting.significance import paired_difference_summary

NUMERIC_METRICS = [
    "lp_minus_hodl_b",
    "total_lp_revenue_b",
    "total_attributed_loss_b",
    "total_trader_cost_b",
    "total_arbitrage_profit_b",
    "lysis_count",
    "active_cell_count",
    "top_cell_concentration_final",
    "failure_modes_count",
]


def aggregate_result_rows(
    rows: Sequence[dict[str, Any]],
    *,
    group_by: Sequence[str],
    bootstrap_seed: int = 7,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(field) for field in group_by)].append(row)

    aggregate_rows: list[dict[str, Any]] = []
    for key, members in grouped.items():
        aggregate_row = {field: value for field, value in zip(group_by, key, strict=True)}
        aggregate_row["count"] = len(members)
        for metric in NUMERIC_METRICS:
            values = [float(member[metric]) for member in members if member.get(metric) is not None]
            aggregate_row.update(_summarize_metric(metric, values, bootstrap_seed=bootstrap_seed))
            if metric == "lp_minus_hodl_b":
                aggregate_row["downside_frequency_lp_minus_hodl_b"] = (
                    sum(value < 0.0 for value in values) / len(values) if values else 0.0
                )
        aggregate_rows.append(aggregate_row)
    return aggregate_rows


def add_comparator_summaries(
    aggregate_rows: Sequence[dict[str, Any]],
    rows: Sequence[dict[str, Any]],
    *,
    contender_model: str,
    comparator_model: str,
) -> dict[str, Any]:
    return {
        "lp_minus_hodl": paired_difference_summary(
            rows,
            contender_model=contender_model,
            comparator_model=comparator_model,
            metric_key="lp_minus_hodl_b",
        ),
        "trader_cost": paired_difference_summary(
            rows,
            contender_model=contender_model,
            comparator_model=comparator_model,
            metric_key="total_trader_cost_b",
        ),
    }


def _summarize_metric(metric: str, values: Sequence[float], *, bootstrap_seed: int) -> dict[str, Any]:
    if not values:
        return {
            f"{metric}_mean": 0.0,
            f"{metric}_median": 0.0,
            f"{metric}_std": 0.0,
            f"{metric}_min": 0.0,
            f"{metric}_max": 0.0,
            f"{metric}_p25": 0.0,
            f"{metric}_p75": 0.0,
            f"{metric}_ci_lower": 0.0,
            f"{metric}_ci_upper": 0.0,
        }
    ci = bootstrap_confidence_interval(values, metric="median", seed=bootstrap_seed)
    return {
        f"{metric}_mean": statistics.fmean(values),
        f"{metric}_median": float(statistics.median(values)),
        f"{metric}_std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        f"{metric}_min": min(values),
        f"{metric}_max": max(values),
        f"{metric}_p25": _quantile(values, 0.25),
        f"{metric}_p75": _quantile(values, 0.75),
        f"{metric}_ci_lower": float(ci["lower"]),
        f"{metric}_ci_upper": float(ci["upper"]),
    }


def _quantile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)
