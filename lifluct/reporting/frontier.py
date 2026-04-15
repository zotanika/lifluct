"""Frontier analysis helpers for Phase 4 thesis adjudication."""

from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from lifluct.constants import DEFAULT_PLOTS_DIRNAME, PLOT_FILE_NAMES
from lifluct.reporting.plots import (
    plot_attributed_loss_vs_oracle_lag,
    plot_best_fixed_vs_lifluct_comparison,
    plot_lp_vs_trader_frontier,
    plot_lysis_count_vs_oracle_lag,
    plot_metric_heatmap,
    plot_metric_vs_parameter,
)
from lifluct.reporting.tables import markdown_table, write_rows_csv


def compute_lp_vs_trader_frontier(
    rows: Sequence[dict[str, Any]],
    *,
    baseline_model_type: str = "dynamic_fee_single",
) -> list[dict[str, Any]]:
    baselines = _baseline_lookup(rows, baseline_model_type=baseline_model_type)
    frontier_rows: list[dict[str, Any]] = []
    for row in rows:
        baseline = baselines.get(_match_key(row))
        if baseline is None:
            continue
        frontier_rows.append(
            {
                "label": row.get("label", row.get("model_type", "run")),
                "model_type": row.get("model_type", row.get("baseline_type", "run")),
                "seed": row.get("seed"),
                "sigma": row.get("sigma"),
                "oracle_lag_steps": row.get("oracle_lag_steps"),
                "toxic_mode": row.get("toxic_mode"),
                "lp_improvement_vs_baseline_b": float(row["lp_minus_hodl_b"]) - float(baseline["lp_minus_hodl_b"]),
                "trader_cost_increase_vs_baseline_b": float(row["total_trader_cost_b"]) - float(baseline["total_trader_cost_b"]),
            }
        )
    return frontier_rows


def generate_frontier_outputs(
    rows: Sequence[dict[str, Any]],
    *,
    output_dir: str | Path,
    baseline_model_type: str = "dynamic_fee_single",
) -> dict[str, Any]:
    output_root = Path(output_dir)
    plots_dir = output_root / DEFAULT_PLOTS_DIRNAME
    plots_dir.mkdir(parents=True, exist_ok=True)

    effective_baseline = baseline_model_type
    families = {str(row.get("model_family", "")) for row in rows}
    if families == {"lysis_enabled"}:
        effective_baseline = "dynamic_fee_single_with_lysis"
    frontier_rows = compute_lp_vs_trader_frontier(rows, baseline_model_type=effective_baseline)
    best_fixed_baseline = "best_fixed_single_cell_with_lysis" if families == {"lysis_enabled"} else "best_fixed_single_cell"
    frontier_rows_best_fixed = compute_lp_vs_trader_frontier(rows, baseline_model_type=best_fixed_baseline)
    write_rows_csv(output_root / "frontier_rows.csv", frontier_rows)
    write_rows_csv(output_root / "frontier_rows_vs_best_fixed.csv", frontier_rows_best_fixed)

    plot_paths: dict[str, Path] = {}
    if frontier_rows:
        plot_paths["lp_vs_trader_frontier"] = plot_lp_vs_trader_frontier(
            frontier_rows,
            plots_dir / PLOT_FILE_NAMES["lp_vs_trader_frontier"],
            title=f"LP Improvement Vs Trader Cost Increase ({effective_baseline})",
        )
    if frontier_rows_best_fixed:
        plot_paths["lp_vs_trader_frontier_vs_best_fixed"] = plot_lp_vs_trader_frontier(
            frontier_rows_best_fixed,
            plots_dir / PLOT_FILE_NAMES["lp_vs_trader_frontier_vs_best_fixed"],
            title=f"LP Improvement Vs Trader Cost Increase ({best_fixed_baseline})",
        )
    if _has_variation(rows, "oracle_lag_steps"):
        plot_paths["lp_minus_hodl_vs_oracle_lag"] = plot_metric_vs_parameter(
            rows,
            parameter_key="oracle_lag_steps",
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["lp_minus_hodl_vs_oracle_lag"],
            title="LP Minus HODL Vs Oracle Lag",
            group_key="model_type" if _has_variation(rows, "model_type") else "baseline_type",
        )
        plot_paths["attributed_loss_vs_oracle_lag"] = plot_attributed_loss_vs_oracle_lag(
            rows,
            plots_dir / PLOT_FILE_NAMES["attributed_loss_vs_oracle_lag"],
        )
        plot_paths["lysis_count_vs_oracle_lag"] = plot_lysis_count_vs_oracle_lag(
            rows,
            plots_dir / PLOT_FILE_NAMES["lysis_count_vs_oracle_lag"],
        )
    if _has_variation(rows, "sigma"):
        plot_paths["lp_minus_hodl_vs_sigma"] = plot_metric_vs_parameter(
            rows,
            parameter_key="sigma",
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["lp_minus_hodl_vs_sigma"],
            title="LP Minus HODL Vs Sigma",
            group_key="model_type" if _has_variation(rows, "model_type") else "baseline_type",
        )
    if _has_variation(rows, "omega") and _has_variation(rows, "sigma"):
        plot_paths["lp_outcome_heatmap_omega_sigma"] = plot_metric_heatmap(
            rows,
            x_key="omega",
            y_key="sigma",
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["lp_outcome_heatmap_omega_sigma"],
            title="LP Outcome Across (Omega, Sigma)",
        )
    if _has_variation(rows, "oracle_lag_steps") and _has_variation(rows, "kappa"):
        plot_paths["lp_outcome_heatmap_oracle_lag_kappa"] = plot_metric_heatmap(
            rows,
            x_key="oracle_lag_steps",
            y_key="kappa",
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["lp_outcome_heatmap_oracle_lag_kappa"],
            title="LP Outcome Across (Oracle Lag, Kappa)",
        )
    if _has_best_fixed_and_turgor(rows):
        plot_paths["best_fixed_vs_turgor"] = plot_best_fixed_vs_lifluct_comparison(
            rows,
            plots_dir / PLOT_FILE_NAMES["best_fixed_vs_turgor"],
        )

    return {
        "frontier_rows": frontier_rows,
        "frontier_table": "\n\n".join(
            [
                "### Vs Dynamic Baseline",
                markdown_table(frontier_rows),
                "### Vs Best Fixed Single-Cell",
                markdown_table(frontier_rows_best_fixed),
            ]
        ),
        "plot_paths": plot_paths,
        "observations": frontier_observations(frontier_rows, rows) + frontier_observations(frontier_rows_best_fixed, rows, baseline_label=best_fixed_baseline),
    }


def frontier_observations(
    frontier_rows: Sequence[dict[str, Any]],
    rows: Sequence[dict[str, Any]],
    *,
    baseline_label: str = "baseline",
) -> list[str]:
    observations: list[str] = []
    if frontier_rows:
        best_lp = max(frontier_rows, key=lambda row: float(row["lp_improvement_vs_baseline_b"]))
        worst_trader = max(frontier_rows, key=lambda row: float(row["trader_cost_increase_vs_baseline_b"]))
        observations.append(
            f"Best LP improvement vs `{baseline_label}` came from `{best_lp['label']}` at `{float(best_lp['lp_improvement_vs_baseline_b']):.6f}`."
        )
        observations.append(
            f"Largest trader-cost increase vs `{baseline_label}` came from `{worst_trader['label']}` at `{float(worst_trader['trader_cost_increase_vs_baseline_b']):.6f}`."
        )
        if any(float(row["trader_cost_increase_vs_baseline_b"]) > 0.0 for row in frontier_rows):
            observations.append("Some LP improvements came with higher trader cost, so Pareto discipline matters.")
    if _has_variation(rows, "oracle_lag_steps"):
        observations.append("Oracle-lag sweeps are present; inspect the lag frontier before drawing strong conclusions.")
    return observations or ["No frontier observations were available."]


def _baseline_lookup(
    rows: Sequence[dict[str, Any]],
    *,
    baseline_model_type: str,
) -> dict[tuple[Any, ...], dict[str, Any]]:
    lookup: dict[tuple[Any, ...], dict[str, Any]] = {}
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("model_type", row.get("baseline_type")) != baseline_model_type:
            continue
        grouped[_match_key(row)].append(row)
    for key, members in grouped.items():
        lookup[key] = {
            **members[0],
            "lp_minus_hodl_b": statistics.fmean(float(member["lp_minus_hodl_b"]) for member in members),
            "total_trader_cost_b": statistics.fmean(float(member["total_trader_cost_b"]) for member in members),
        }
    return lookup


def _match_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("evaluation_split"),
        row.get("regime_id"),
        row.get("seed"),
        row.get("sigma"),
        row.get("oracle_lag_steps"),
        row.get("toxic_mode"),
        row.get("fitness_mode"),
        row.get("lysis_mode"),
    )


def _has_variation(rows: Sequence[dict[str, Any]], key: str) -> bool:
    return len({row.get(key) for row in rows}) > 1


def _has_best_fixed_and_turgor(rows: Sequence[dict[str, Any]]) -> bool:
    model_types = {row.get("model_type", row.get("baseline_type")) for row in rows}
    return any(
        pair.issubset(model_types)
        for pair in [
            {"best_fixed_single_cell", "lifluct_multi_cell"},
            {"best_fixed_single_cell", "lifluct_multi_cell_no_lysis"},
            {"best_fixed_single_cell_with_lysis", "lifluct_multi_cell_with_lysis"},
        ]
    )
