"""Transparent verdict logic for Phase 4.2 thesis adjudication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from lifluct.reporting.significance import paired_difference_summary


@dataclass(slots=True)
class AdjudicationResult:
    family_name: str
    verdict: str
    reasons: list[str]
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_name": self.family_name,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
            **self.evidence,
        }


def adjudicate_family(
    rows: Sequence[dict[str, Any]],
    prevalence_rows: Sequence[dict[str, Any]],
    *,
    family_name: str,
    model_family: str,
    min_samples: int = 8,
    trader_cost_tolerance_b: float = 0.0,
    best_fixed_tolerance_b: float = 0.0,
    extreme_failure_prevalence: float = 0.50,
    critical_failure_prevalence: float = 0.25,
) -> AdjudicationResult:
    dynamic_model = "dynamic_fee_single_with_lysis" if model_family == "lysis_enabled" else "dynamic_fee_single"
    best_fixed_model = "best_fixed_single_cell_with_lysis" if model_family == "lysis_enabled" else "best_fixed_single_cell"
    lifluct_model = "lifluct_multi_cell_with_lysis" if model_family == "lysis_enabled" else "lifluct_multi_cell_no_lysis"

    lp_vs_dynamic = paired_difference_summary(
        rows,
        contender_model=lifluct_model,
        comparator_model=dynamic_model,
        metric_key="lp_minus_hodl_b",
    )
    lp_vs_best_fixed = paired_difference_summary(
        rows,
        contender_model=lifluct_model,
        comparator_model=best_fixed_model,
        metric_key="lp_minus_hodl_b",
    )
    trader_vs_dynamic = paired_difference_summary(
        rows,
        contender_model=lifluct_model,
        comparator_model=dynamic_model,
        metric_key="total_trader_cost_b",
    )

    critical_prevalence = _failure_prevalence(prevalence_rows, model=lifluct_model, severity="critical")
    avg_failure_flags = _average_failure_flags(prevalence_rows, model=lifluct_model)
    sample_count = min(
        int(lp_vs_dynamic["count"]),
        int(lp_vs_best_fixed["count"]),
    )

    reasons: list[str] = []
    evidence = {
        "sample_count": sample_count,
        "lp_vs_dynamic_median_diff": lp_vs_dynamic["median_diff"],
        "lp_vs_best_fixed_median_diff": lp_vs_best_fixed["median_diff"],
        "trader_cost_vs_dynamic_median_diff": trader_vs_dynamic["median_diff"],
        "critical_failure_prevalence": critical_prevalence,
        "avg_failure_flags_per_run": avg_failure_flags,
    }

    if sample_count < min_samples:
        reasons.append(
            f"Only {sample_count} paired samples were available, which is below the default minimum of {min_samples}."
        )
        return AdjudicationResult(family_name=family_name, verdict="inconclusive", reasons=reasons, evidence=evidence)

    if float(lp_vs_dynamic["median_diff"]) <= 0.0 and float(lp_vs_best_fixed["median_diff"]) < -best_fixed_tolerance_b:
        reasons.append("LIFLUCT underperformed both the dynamic baseline and the best fixed single-cell benchmark on median LP-minus-HODL.")
        return AdjudicationResult(family_name=family_name, verdict="fails", reasons=reasons, evidence=evidence)

    if critical_prevalence >= critical_failure_prevalence or avg_failure_flags >= extreme_failure_prevalence:
        reasons.append("Failure-flag prevalence was high enough to make the family outcome look structurally fragile.")
        if float(lp_vs_dynamic["median_diff"]) > 0.0:
            return AdjudicationResult(family_name=family_name, verdict="mixed", reasons=reasons, evidence=evidence)
        return AdjudicationResult(family_name=family_name, verdict="fails", reasons=reasons, evidence=evidence)

    if (
        float(lp_vs_dynamic["median_diff"]) > 0.0
        and float(lp_vs_best_fixed["median_diff"]) >= -best_fixed_tolerance_b
        and float(trader_vs_dynamic["median_diff"]) <= trader_cost_tolerance_b
    ):
        reasons.append("LIFLUCT cleared the default median LP hurdle against the dynamic baseline without conceding the best fixed benchmark or trader-cost tolerance.")
        return AdjudicationResult(family_name=family_name, verdict="survives", reasons=reasons, evidence=evidence)

    if (
        float(lp_vs_dynamic["median_diff"]) > 0.0
        or float(lp_vs_best_fixed["median_diff"]) > -best_fixed_tolerance_b
    ):
        reasons.append("LIFLUCT showed some LP upside, but the result remains qualified by trader cost, fixed-baseline pressure, or instability.")
        return AdjudicationResult(family_name=family_name, verdict="mixed", reasons=reasons, evidence=evidence)

    reasons.append("The available paired evidence does not support a clean family-level survival claim.")
    return AdjudicationResult(family_name=family_name, verdict="fails", reasons=reasons, evidence=evidence)


def _failure_prevalence(rows: Sequence[dict[str, Any]], *, model: str, severity: str) -> float:
    matching = [row for row in rows if str(row.get("model_type", row.get("model_type", ""))) == model and str(row.get("severity", "")) == severity]
    if not matching:
        return 0.0
    return max(float(row["fraction_of_runs"]) for row in matching)


def _average_failure_flags(rows: Sequence[dict[str, Any]], *, model: str) -> float:
    matching = [row for row in rows if str(row.get("model_type", row.get("model_type", ""))) == model]
    if not matching:
        return 0.0
    return max(float(row["avg_failure_flags_per_run"]) for row in matching)
