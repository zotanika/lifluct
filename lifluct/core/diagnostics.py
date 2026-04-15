"""Heuristic diagnostics for Phase 4 stability and concentration analysis."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Sequence

from lifluct.types import CellSnapshot, EpochSummary, RunConfig, RunSummary, StepMetric


def active_cells_by_epoch(epoch_summaries: Sequence[EpochSummary]) -> dict[int, int]:
    return {epoch.epoch_index: epoch.num_active_cells for epoch in epoch_summaries}


def mean_fitness_by_epoch(epoch_summaries: Sequence[EpochSummary]) -> dict[int, float]:
    return {epoch.epoch_index: epoch.mean_fitness for epoch in epoch_summaries}


def gene_variance_by_epoch(cell_snapshots: Sequence[CellSnapshot]) -> dict[int, float]:
    if not cell_snapshots:
        return {}
    epochs = sorted({snapshot.epoch_index for snapshot in cell_snapshots})
    variance_map: dict[int, float] = {}
    for epoch_index in epochs:
        snapshots = [snapshot for snapshot in cell_snapshots if snapshot.epoch_index == epoch_index]
        if len(snapshots) <= 1:
            variance_map[epoch_index] = 0.0
            continue
        components = []
        for field_name in ("f_min", "mu", "tau", "beta"):
            values = [getattr(snapshot, field_name) for snapshot in snapshots]
            components.append(statistics.pvariance(values))
        variance_map[epoch_index] = statistics.fmean(components)
    return variance_map


def top_k_cell_volume_share_by_epoch(
    cell_snapshots: Sequence[CellSnapshot],
    *,
    k: int,
) -> dict[int, float]:
    if not cell_snapshots:
        return {}
    grouped: dict[int, list[CellSnapshot]] = defaultdict(list)
    for snapshot in cell_snapshots:
        grouped[snapshot.epoch_index].append(snapshot)

    shares: dict[int, float] = {}
    for epoch_index, snapshots in grouped.items():
        volumes = sorted((snapshot.epoch_volume_b for snapshot in snapshots), reverse=True)
        total_volume = sum(volumes)
        if total_volume <= 0.0:
            shares[epoch_index] = 0.0
            continue
        shares[epoch_index] = sum(volumes[:k]) / total_volume
    return shares


def lysis_count_by_epoch(epoch_summaries: Sequence[EpochSummary]) -> dict[int, int]:
    return {epoch.epoch_index: epoch.num_lysed_cells for epoch in epoch_summaries}


def extinction_count_by_epoch(epoch_summaries: Sequence[EpochSummary]) -> dict[int, int]:
    return {epoch.epoch_index: epoch.num_dead_cells for epoch in epoch_summaries}


def final_gene_dispersion(cell_snapshots: Sequence[CellSnapshot]) -> float:
    variance_map = gene_variance_by_epoch(cell_snapshots)
    if not variance_map:
        return 0.0
    return variance_map[max(variance_map.keys())] ** 0.5


def oscillation_score(
    epoch_summaries: Sequence[EpochSummary],
    cell_snapshots: Sequence[CellSnapshot],
) -> float:
    """
    Heuristic instability score.

    This is deliberately simple: more sign changes in mean fitness and weaker
    contraction in gene variance both increase the score.
    """
    if len(epoch_summaries) < 2:
        return 0.0

    mean_fitness = [epoch.mean_fitness for epoch in epoch_summaries]
    sign_changes = 0
    swing_sum = 0.0
    for previous, current in zip(mean_fitness, mean_fitness[1:]):
        if (previous < 0.0 < current) or (previous > 0.0 > current):
            sign_changes += 1
        swing_sum += abs(current - previous)

    variance_series = list(gene_variance_by_epoch(cell_snapshots).values())
    if variance_series:
        contraction_ratio = variance_series[-1] / max(variance_series[0], 1e-12)
    else:
        contraction_ratio = 0.0

    return float(sign_changes + swing_sum + max(0.0, contraction_ratio - 1.0))


def dead_volume_score(
    config: RunConfig,
    summary: RunSummary,
    epoch_summaries: Sequence[EpochSummary],
) -> float:
    """
    Heuristic dead-volume score.

    Low total volume relative to initial TVL and high average fees push this score up.
    """
    initial_tvl_b = config.initial_reserve_a * config.initial_price + config.initial_reserve_b
    if initial_tvl_b <= 0.0:
        return 0.0
    avg_epoch_volume = (
        statistics.fmean(epoch.total_volume_b for epoch in epoch_summaries)
        if epoch_summaries
        else 0.0
    )
    avg_fee = (
        statistics.fmean(epoch.avg_fee_rate for epoch in epoch_summaries)
        if epoch_summaries
        else config.f_min
    )
    volume_component = max(0.0, 1.0 - (avg_epoch_volume / initial_tvl_b))
    fee_component = avg_fee / max(config.fee_max_global, 1e-12)
    return float(volume_component + fee_component)


def summarize_result_diagnostics(
    *,
    config: RunConfig,
    summary: RunSummary,
    epoch_summaries: Sequence[EpochSummary],
    cell_snapshots: Sequence[CellSnapshot],
    step_metrics: Sequence[StepMetric],
) -> dict[str, Any]:
    top_1_share = top_k_cell_volume_share_by_epoch(cell_snapshots, k=1)
    top_2_share = top_k_cell_volume_share_by_epoch(cell_snapshots, k=2)
    return {
        "active_cells_by_epoch": active_cells_by_epoch(epoch_summaries),
        "mean_fitness_by_epoch": mean_fitness_by_epoch(epoch_summaries),
        "gene_variance_by_epoch": gene_variance_by_epoch(cell_snapshots),
        "top_1_cell_volume_share_by_epoch": top_1_share,
        "top_2_cell_volume_share_by_epoch": top_2_share,
        "lysis_count_by_epoch": lysis_count_by_epoch(epoch_summaries),
        "extinction_count_by_epoch": extinction_count_by_epoch(epoch_summaries),
        "final_gene_dispersion": final_gene_dispersion(cell_snapshots),
        "oscillation_score": oscillation_score(epoch_summaries, cell_snapshots),
        "dead_volume_score": dead_volume_score(config, summary, epoch_summaries),
        "final_active_cells": step_metrics[-1].num_active_cells if step_metrics else 0,
    }
