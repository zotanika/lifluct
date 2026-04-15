"""Bootstrap helpers for aggregate experiment statistics."""

from __future__ import annotations

import statistics
from typing import Sequence

import numpy as np


def bootstrap_confidence_interval(
    values: Sequence[float],
    *,
    metric: str = "mean",
    confidence: float = 0.95,
    num_bootstrap: int = 500,
    seed: int = 7,
) -> dict[str, float | int | str]:
    if not values:
        return {
            "metric": metric,
            "center": 0.0,
            "lower": 0.0,
            "upper": 0.0,
            "num_samples": 0,
            "num_bootstrap": num_bootstrap,
        }
    rng = np.random.default_rng(seed)
    sample = np.asarray(list(values), dtype=float)
    estimates = []
    for _ in range(max(1, num_bootstrap)):
        draw = rng.choice(sample, size=len(sample), replace=True)
        estimates.append(_estimate(draw.tolist(), metric=metric))
    alpha = max(0.0, min(1.0, (1.0 - confidence) / 2.0))
    lower = float(np.quantile(estimates, alpha))
    upper = float(np.quantile(estimates, 1.0 - alpha))
    center = _estimate(list(values), metric=metric)
    return {
        "metric": metric,
        "center": center,
        "lower": lower,
        "upper": upper,
        "num_samples": len(values),
        "num_bootstrap": num_bootstrap,
    }


def _estimate(values: Sequence[float], *, metric: str) -> float:
    if metric == "mean":
        return statistics.fmean(values)
    if metric == "median":
        return float(statistics.median(values))
    raise ValueError(f"unsupported bootstrap metric: {metric}")
