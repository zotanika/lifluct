"""Matplotlib plot helpers for the LIFLUCT simulator."""

from __future__ import annotations

import os
import statistics
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

_CACHE_ROOT = Path(tempfile.gettempdir()) / "lifluct-mpl-cache"
_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
(_CACHE_ROOT / "matplotlib").mkdir(parents=True, exist_ok=True)
(_CACHE_ROOT / "xdg").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE_ROOT / "xdg"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from lifluct.constants import PLOT_FILE_NAMES
from lifluct.types import CellSnapshot, EpochSummary, StepMetric


def plot_lp_value_vs_hodl(step_metrics: Sequence[StepMetric], output_path: str | Path) -> Path:
    output = Path(output_path)
    plt.figure(figsize=(9, 5))
    plt.plot([metric.step for metric in step_metrics], [metric.lp_value_b for metric in step_metrics], label="LP value")
    plt.plot([metric.step for metric in step_metrics], [metric.hodl_value_b for metric in step_metrics], label="HODL value")
    plt.xlabel("Step")
    plt.ylabel("Value (asset-B)")
    plt.title("LP Value Vs HODL")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_cumulative_fees(step_metrics: Sequence[StepMetric], output_path: str | Path) -> Path:
    output = Path(output_path)
    steps = [metric.step for metric in step_metrics]
    plt.figure(figsize=(9, 5))
    plt.plot(steps, [metric.cumulative_lp_fee_b for metric in step_metrics], label="LP fees")
    plt.plot(steps, [metric.cumulative_protocol_fee_b for metric in step_metrics], label="Protocol fees")
    plt.plot(
        steps,
        [metric.cumulative_lp_fee_b + metric.cumulative_protocol_fee_b for metric in step_metrics],
        label="Total fees",
    )
    plt.xlabel("Step")
    plt.ylabel("Cumulative fees (asset-B)")
    plt.title("Cumulative Fees")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_cumulative_attributed_loss(step_metrics: Sequence[StepMetric], output_path: str | Path) -> Path:
    output = Path(output_path)
    plt.figure(figsize=(9, 5))
    plt.plot([metric.step for metric in step_metrics], [metric.cumulative_attributed_loss_b for metric in step_metrics], label="Attributed loss proxy")
    plt.xlabel("Step")
    plt.ylabel("Cumulative loss (asset-B)")
    plt.title("Cumulative Attributed Loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_cumulative_trader_cost(step_metrics: Sequence[StepMetric], output_path: str | Path) -> Path:
    output = Path(output_path)
    plt.figure(figsize=(9, 5))
    plt.plot([metric.step for metric in step_metrics], [metric.cumulative_trader_cost_b for metric in step_metrics], label="Trader cost proxy")
    plt.xlabel("Step")
    plt.ylabel("Cumulative cost (asset-B)")
    plt.title("Cumulative Trader Cost")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_oracle_vs_pool_price(step_metrics: Sequence[StepMetric], output_path: str | Path) -> Path:
    output = Path(output_path)
    steps = [metric.step for metric in step_metrics]
    plt.figure(figsize=(9, 5))
    plt.plot(steps, [metric.pool_price for metric in step_metrics], label="Pool price")
    plt.plot(steps, [metric.observed_price for metric in step_metrics], label="Observed oracle")
    if any(metric.true_price != metric.observed_price for metric in step_metrics):
        plt.plot(steps, [metric.true_price for metric in step_metrics], label="True price", linestyle="--")
    plt.xlabel("Step")
    plt.ylabel("Price (asset-B per asset-A)")
    plt.title("Oracle Price Vs Pool Price")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_total_attributed_loss_by_epoch(
    epoch_summaries: Sequence[EpochSummary],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    plt.figure(figsize=(9, 5))
    plt.plot([epoch.epoch_index for epoch in epoch_summaries], [epoch.total_attributed_loss_b for epoch in epoch_summaries], marker="o")
    plt.xlabel("Epoch")
    plt.ylabel("Attributed loss (asset-B)")
    plt.title("Total Attributed Loss By Epoch")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_total_lp_revenue_by_epoch(
    epoch_summaries: Sequence[EpochSummary],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    plt.figure(figsize=(9, 5))
    plt.plot([epoch.epoch_index for epoch in epoch_summaries], [epoch.total_lp_revenue_b for epoch in epoch_summaries], marker="o")
    plt.xlabel("Epoch")
    plt.ylabel("LP revenue (asset-B)")
    plt.title("Total LP Revenue By Epoch")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_active_cells_by_epoch(
    epoch_summaries: Sequence[EpochSummary],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    plt.figure(figsize=(9, 5))
    plt.plot([epoch.epoch_index for epoch in epoch_summaries], [epoch.num_active_cells for epoch in epoch_summaries], marker="o")
    plt.xlabel("Epoch")
    plt.ylabel("Active cells")
    plt.title("Active Cells By Epoch")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_lysis_events_by_epoch(
    epoch_summaries: Sequence[EpochSummary],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    plt.figure(figsize=(9, 5))
    plt.bar([epoch.epoch_index for epoch in epoch_summaries], [epoch.num_lysed_cells for epoch in epoch_summaries])
    plt.xlabel("Epoch")
    plt.ylabel("Lysed cells")
    plt.title("Lysis Events By Epoch")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_f_min_trajectories(cell_snapshots: Sequence[CellSnapshot], output_path: str | Path) -> Path:
    return _plot_gene_trajectory(cell_snapshots, output_path, gene_name="f_min", title="f_min Trajectories")


def plot_mu_trajectories(cell_snapshots: Sequence[CellSnapshot], output_path: str | Path) -> Path:
    return _plot_gene_trajectory(cell_snapshots, output_path, gene_name="mu", title="mu Trajectories")


def plot_tau_trajectories(cell_snapshots: Sequence[CellSnapshot], output_path: str | Path) -> Path:
    return _plot_gene_trajectory(cell_snapshots, output_path, gene_name="tau", title="tau Trajectories")


def plot_beta_trajectories(cell_snapshots: Sequence[CellSnapshot], output_path: str | Path) -> Path:
    return _plot_gene_trajectory(cell_snapshots, output_path, gene_name="beta", title="beta Trajectories")


def plot_revenue_vs_loss_scatter(
    cell_snapshots: Sequence[CellSnapshot],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    if not cell_snapshots:
        return _empty_plot(output, title="Per-Cell LP Revenue Vs Attributed Loss")
    final_epoch = max(snapshot.epoch_index for snapshot in cell_snapshots)
    final_snapshots = [snapshot for snapshot in cell_snapshots if snapshot.epoch_index == final_epoch]
    plt.figure(figsize=(9, 5))
    plt.scatter(
        [snapshot.epoch_attributed_loss_b for snapshot in final_snapshots],
        [snapshot.epoch_lp_revenue_b for snapshot in final_snapshots],
    )
    plt.xlabel("Attributed loss (asset-B)")
    plt.ylabel("LP revenue (asset-B)")
    plt.title("Per-Cell LP Revenue Vs Attributed Loss")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_surviving_genes_histogram(
    cell_snapshots: Sequence[CellSnapshot],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    if not cell_snapshots:
        return _empty_plot(output, title="Histogram Of Surviving Final-Epoch Genes")
    final_epoch = max(snapshot.epoch_index for snapshot in cell_snapshots)
    final_survivors = [snapshot for snapshot in cell_snapshots if snapshot.epoch_index == final_epoch and snapshot.active]
    if not final_survivors:
        return _empty_plot(output, title="Histogram Of Surviving Final-Epoch Genes")
    plt.figure(figsize=(9, 5))
    plt.hist([snapshot.mu for snapshot in final_survivors], bins=10, alpha=0.7, label="mu")
    plt.hist([snapshot.f_min for snapshot in final_survivors], bins=10, alpha=0.5, label="f_min")
    plt.xlabel("Gene value")
    plt.ylabel("Count")
    plt.title("Histogram Of Surviving Final-Epoch Genes")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_gene_variance_by_epoch(
    cell_snapshots: Sequence[CellSnapshot],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    if not cell_snapshots:
        return _empty_plot(output, title="Gene Variance By Epoch")
    variance_series = _gene_variance_by_epoch(cell_snapshots)
    plt.figure(figsize=(9, 5))
    plt.plot(list(variance_series.keys()), list(variance_series.values()), marker="o")
    plt.xlabel("Epoch")
    plt.ylabel("Average gene variance")
    plt.title("Gene Variance By Epoch")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_all_cells_inactive_over_time(
    step_metrics: Sequence[StepMetric],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    plt.figure(figsize=(9, 5))
    plt.plot(
        [metric.step for metric in step_metrics],
        [1 if metric.num_active_cells == 0 else 0 for metric in step_metrics],
    )
    plt.xlabel("Step")
    plt.ylabel("All cells inactive (1=yes)")
    plt.title("All Cells Inactive Over Time")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_lysis_cascade_timeline(
    epoch_summaries: Sequence[EpochSummary],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    if not epoch_summaries:
        return _empty_plot(output, title="Lysis Cascade Timeline")
    plt.figure(figsize=(9, 5))
    plt.plot(
        [epoch.epoch_index for epoch in epoch_summaries],
        [epoch.num_lysed_cells for epoch in epoch_summaries],
        marker="o",
    )
    plt.xlabel("Epoch")
    plt.ylabel("Lysed cells")
    plt.title("Lysis Cascade Timeline")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_top_cell_concentration_by_epoch(
    cell_snapshots: Sequence[CellSnapshot],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    if not cell_snapshots:
        return _empty_plot(output, title="Top-Cell Concentration By Epoch")
    grouped: dict[int, list[CellSnapshot]] = defaultdict(list)
    for snapshot in cell_snapshots:
        grouped[snapshot.epoch_index].append(snapshot)
    epochs = sorted(grouped.keys())
    shares = []
    for epoch in epochs:
        volumes = sorted((snapshot.epoch_volume_b for snapshot in grouped[epoch]), reverse=True)
        total_volume = sum(volumes)
        shares.append((volumes[0] / total_volume) if total_volume > 0.0 else 0.0)
    plt.figure(figsize=(9, 5))
    plt.plot(epochs, shares, marker="o")
    plt.xlabel("Epoch")
    plt.ylabel("Top-1 volume share")
    plt.title("Top-Cell Concentration By Epoch")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_lp_vs_trader_frontier(
    rows: Sequence[dict[str, Any]],
    output_path: str | Path,
    *,
    title: str,
) -> Path:
    output = Path(output_path)
    if not rows:
        return _empty_plot(output, title=title)
    plt.figure(figsize=(9, 5))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("model_type", row.get("label", "run")))].append(row)
    for group_name, group_rows in groups.items():
        plt.scatter(
            [float(row["trader_cost_increase_vs_baseline_b"]) for row in group_rows],
            [float(row["lp_improvement_vs_baseline_b"]) for row in group_rows],
            label=group_name,
            alpha=0.8,
        )
    plt.axhline(0.0, color="black", linewidth=0.8, linestyle="--")
    plt.axvline(0.0, color="black", linewidth=0.8, linestyle="--")
    plt.xlabel("Trader cost increase vs baseline (asset-B)")
    plt.ylabel("LP improvement vs baseline (asset-B)")
    plt.title(title)
    if len(groups) > 1:
        plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_attributed_loss_vs_oracle_lag(
    rows: Sequence[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    return plot_metric_vs_parameter(
        rows,
        parameter_key="oracle_lag_steps",
        metric_key="total_attributed_loss_b",
        output_path=output_path,
        title="Attributed Loss Vs Oracle Lag",
        group_key="model_type" if len({row.get('model_type') for row in rows}) > 1 else "baseline_type",
    )


def plot_lysis_count_vs_oracle_lag(
    rows: Sequence[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    return plot_metric_vs_parameter(
        rows,
        parameter_key="oracle_lag_steps",
        metric_key="lysis_count",
        output_path=output_path,
        title="Lysis Count Vs Oracle Lag",
        group_key="model_type" if len({row.get('model_type') for row in rows}) > 1 else "baseline_type",
    )


def plot_attribution_mode_ranking_stability(
    rows: Sequence[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    if not rows:
        return _empty_plot(output, title="Attribution Mode Ranking Stability")
    labels = [str(row["mode"]) for row in rows]
    loss_corr = [float(row["loss_rank_correlation"]) for row in rows]
    fitness_corr = [float(row["fitness_rank_correlation"]) for row in rows]
    x = np.arange(len(labels))
    width = 0.35
    plt.figure(figsize=(10, 5))
    plt.bar(x - width / 2, loss_corr, width=width, label="loss rank")
    plt.bar(x + width / 2, fitness_corr, width=width, label="fitness rank")
    plt.xticks(x, labels, rotation=25, ha="right")
    plt.ylim(-1.0, 1.05)
    plt.ylabel("Correlation vs observed_spot")
    plt.title("Attribution Mode Ranking Stability")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_best_fixed_vs_lifluct_comparison(
    rows: Sequence[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    if not rows:
        return _empty_plot(output, title="Best Fixed Single-Cell Vs LIFLUCT")
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        model_type = str(row.get("model_type", row.get("baseline_type", "run")))
        if model_type not in {
            "best_fixed_single_cell",
            "best_fixed_single_cell_with_lysis",
            "lifluct_multi_cell",
            "lifluct_multi_cell_no_lysis",
            "lifluct_multi_cell_with_lysis",
        }:
            continue
        grouped[model_type].append(float(row["lp_minus_hodl_b"]))
    if not grouped:
        return _empty_plot(output, title="Best Fixed Single-Cell Vs LIFLUCT")
    labels = list(grouped.keys())
    means = [statistics.fmean(grouped[label]) for label in labels]
    plt.figure(figsize=(9, 5))
    plt.bar(labels, means)
    plt.ylabel("Mean LP minus HODL (asset-B)")
    plt.title("Best Fixed Single-Cell Vs LIFLUCT")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_failure_regime_timeline(
    step_metrics: Sequence[StepMetric],
    epoch_summaries: Sequence[EpochSummary],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    if not step_metrics:
        return _empty_plot(output, title="Failure Regime Timeline")
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.plot(
        [metric.step for metric in step_metrics],
        [metric.num_active_cells for metric in step_metrics],
        label="active cells",
    )
    axis.set_xlabel("Step")
    axis.set_ylabel("Active cells")
    axis.set_title("Failure Regime Timeline")
    if epoch_summaries:
        twin = axis.twinx()
        twin.step(
            [epoch.epoch_index for epoch in epoch_summaries],
            [epoch.num_lysed_cells for epoch in epoch_summaries],
            where="post",
            color="tab:red",
            label="lysed cells",
        )
        twin.set_ylabel("Lysed cells")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return output


def plot_metric_vs_parameter(
    rows: Sequence[dict[str, Any]],
    *,
    parameter_key: str,
    metric_key: str,
    output_path: str | Path,
    title: str,
    group_key: str = "baseline_type",
) -> Path:
    output = Path(output_path)
    if not rows:
        return _empty_plot(output, title=title)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(group_key, "group"))].append(row)

    plt.figure(figsize=(9, 5))
    for group_name, group_rows in grouped.items():
        grouped_by_param: dict[float, list[float]] = defaultdict(list)
        for row in group_rows:
            param_value = row.get(parameter_key)
            metric_value = row.get(metric_key)
            if param_value is None or metric_value is None:
                continue
            grouped_by_param[float(param_value)].append(float(metric_value))
        if not grouped_by_param:
            continue
        xs = sorted(grouped_by_param.keys())
        ys = [statistics.fmean(grouped_by_param[x]) for x in xs]
        plt.plot(xs, ys, marker="o", label=group_name)
    plt.xlabel(parameter_key)
    plt.ylabel(metric_key)
    plt.title(title)
    if len(grouped) > 1:
        plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_metric_heatmap(
    rows: Sequence[dict[str, Any]],
    *,
    x_key: str,
    y_key: str,
    metric_key: str,
    output_path: str | Path,
    title: str,
) -> Path:
    output = Path(output_path)
    if not rows:
        return _empty_plot(output, title=title)

    x_values = sorted({float(row[x_key]) for row in rows if row.get(x_key) is not None})
    y_values = sorted({float(row[y_key]) for row in rows if row.get(y_key) is not None})
    if not x_values or not y_values:
        return _empty_plot(output, title=title)

    grouped: dict[tuple[float, float], list[float]] = defaultdict(list)
    for row in rows:
        if row.get(x_key) is None or row.get(y_key) is None or row.get(metric_key) is None:
            continue
        grouped[(float(row[x_key]), float(row[y_key]))].append(float(row[metric_key]))

    matrix = np.full((len(y_values), len(x_values)), np.nan)
    for y_index, y_value in enumerate(y_values):
        for x_index, x_value in enumerate(x_values):
            values = grouped.get((x_value, y_value))
            if values:
                matrix[y_index, x_index] = statistics.fmean(values)

    plt.figure(figsize=(9, 6))
    image = plt.imshow(matrix, aspect="auto", origin="lower")
    plt.colorbar(image, label=metric_key)
    plt.xticks(range(len(x_values)), [str(value) for value in x_values], rotation=45)
    plt.yticks(range(len(y_values)), [str(value) for value in y_values])
    plt.xlabel(x_key)
    plt.ylabel(y_key)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_seed_variance_by_group(
    rows: Sequence[dict[str, Any]],
    *,
    group_key: str,
    metric_key: str,
    output_path: str | Path,
    title: str,
) -> Path:
    output = Path(output_path)
    if not rows:
        return _empty_plot(output, title=title)
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row.get(group_key) is None or row.get(metric_key) is None:
            continue
        grouped[str(row[group_key])].append(float(row[metric_key]))
    if not grouped:
        return _empty_plot(output, title=title)

    labels = list(grouped.keys())
    means = [statistics.fmean(values) for values in grouped.values()]
    stds = [statistics.pstdev(values) if len(values) > 1 else 0.0 for values in grouped.values()]

    plt.figure(figsize=(9, 5))
    plt.errorbar(labels, means, yerr=stds, fmt="o")
    plt.xlabel(group_key)
    plt.ylabel(metric_key)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def generate_all_plots(
    step_metrics: Sequence[StepMetric],
    output_dir: str | Path,
    *,
    epoch_summaries: Sequence[EpochSummary] | None = None,
    cell_snapshots: Sequence[CellSnapshot] | None = None,
) -> dict[str, Path]:
    plots_dir = Path(output_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)

    plot_paths = {
        "lp_vs_hodl": plot_lp_value_vs_hodl(step_metrics, plots_dir / PLOT_FILE_NAMES["lp_vs_hodl"]),
        "cumulative_fees": plot_cumulative_fees(step_metrics, plots_dir / PLOT_FILE_NAMES["cumulative_fees"]),
        "cumulative_attributed_loss": plot_cumulative_attributed_loss(step_metrics, plots_dir / PLOT_FILE_NAMES["cumulative_attributed_loss"]),
        "cumulative_trader_cost": plot_cumulative_trader_cost(step_metrics, plots_dir / PLOT_FILE_NAMES["cumulative_trader_cost"]),
        "oracle_vs_pool_price": plot_oracle_vs_pool_price(step_metrics, plots_dir / PLOT_FILE_NAMES["oracle_vs_pool_price"]),
    }

    if epoch_summaries:
        plot_paths.update(
            {
                "epoch_attributed_loss": plot_total_attributed_loss_by_epoch(epoch_summaries, plots_dir / PLOT_FILE_NAMES["epoch_attributed_loss"]),
                "epoch_lp_revenue": plot_total_lp_revenue_by_epoch(epoch_summaries, plots_dir / PLOT_FILE_NAMES["epoch_lp_revenue"]),
                "active_cells": plot_active_cells_by_epoch(epoch_summaries, plots_dir / PLOT_FILE_NAMES["active_cells"]),
                "lysis_events": plot_lysis_events_by_epoch(epoch_summaries, plots_dir / PLOT_FILE_NAMES["lysis_events"]),
            }
        )

    if cell_snapshots:
        plot_paths.update(
            {
                "f_min_trajectories": plot_f_min_trajectories(cell_snapshots, plots_dir / PLOT_FILE_NAMES["f_min_trajectories"]),
                "mu_trajectories": plot_mu_trajectories(cell_snapshots, plots_dir / PLOT_FILE_NAMES["mu_trajectories"]),
                "tau_trajectories": plot_tau_trajectories(cell_snapshots, plots_dir / PLOT_FILE_NAMES["tau_trajectories"]),
                "beta_trajectories": plot_beta_trajectories(cell_snapshots, plots_dir / PLOT_FILE_NAMES["beta_trajectories"]),
                "revenue_vs_loss_scatter": plot_revenue_vs_loss_scatter(cell_snapshots, plots_dir / PLOT_FILE_NAMES["revenue_vs_loss_scatter"]),
                "surviving_gene_histogram": plot_surviving_genes_histogram(cell_snapshots, plots_dir / PLOT_FILE_NAMES["surviving_gene_histogram"]),
                "gene_variance_by_epoch": plot_gene_variance_by_epoch(cell_snapshots, plots_dir / PLOT_FILE_NAMES["gene_variance_by_epoch"]),
                "top_cell_concentration": plot_top_cell_concentration_by_epoch(cell_snapshots, plots_dir / PLOT_FILE_NAMES["top_cell_concentration"]),
            }
        )
    plot_paths["all_cells_inactive_over_time"] = plot_all_cells_inactive_over_time(
        step_metrics,
        plots_dir / PLOT_FILE_NAMES["all_cells_inactive_over_time"],
    )
    if epoch_summaries:
        plot_paths["lysis_cascade_timeline"] = plot_lysis_cascade_timeline(
            epoch_summaries,
            plots_dir / PLOT_FILE_NAMES["lysis_cascade_timeline"],
        )
        plot_paths["failure_regime_timeline"] = plot_failure_regime_timeline(
            step_metrics,
            epoch_summaries,
            plots_dir / PLOT_FILE_NAMES["failure_regime_timeline"],
        )
    return plot_paths


def _plot_gene_trajectory(
    cell_snapshots: Sequence[CellSnapshot],
    output_path: str | Path,
    *,
    gene_name: str,
    title: str,
) -> Path:
    output = Path(output_path)
    plt.figure(figsize=(9, 5))
    cell_ids = sorted({snapshot.cell_id for snapshot in cell_snapshots})
    for cell_id in cell_ids:
        series = [snapshot for snapshot in cell_snapshots if snapshot.cell_id == cell_id]
        plt.plot(
            [snapshot.epoch_index for snapshot in series],
            [getattr(snapshot, gene_name) for snapshot in series],
            alpha=0.7,
        )
    plt.xlabel("Epoch")
    plt.ylabel(gene_name)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def _empty_plot(output_path: Path, *, title: str) -> Path:
    plt.figure(figsize=(9, 5))
    plt.title(title)
    plt.text(0.5, 0.5, "No data available", ha="center", va="center")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path


def _gene_variance_by_epoch(cell_snapshots: Sequence[CellSnapshot]) -> dict[int, float]:
    epochs = sorted({snapshot.epoch_index for snapshot in cell_snapshots})
    variance_series: dict[int, float] = {}
    for epoch in epochs:
        snapshots = [snapshot for snapshot in cell_snapshots if snapshot.epoch_index == epoch]
        if len(snapshots) <= 1:
            variance_series[epoch] = 0.0
            continue
        components = []
        for field_name in ("f_min", "mu", "tau", "beta"):
            values = [getattr(snapshot, field_name) for snapshot in snapshots]
            components.append(statistics.pvariance(values))
        variance_series[epoch] = statistics.fmean(components)
    return variance_series
