"""Explicit failure-mode classification for LIFLUCT research runs."""

from __future__ import annotations

from typing import Any, Sequence

from lifluct.core.diagnostics import (
    dead_volume_score,
    final_gene_dispersion,
    gene_variance_by_epoch,
    oscillation_score,
    top_k_cell_volume_share_by_epoch,
)
from lifluct.types import (
    CellSnapshot,
    EpochSummary,
    FailureModeObservation,
    RunConfig,
    RunSummary,
    StepMetric,
    TradeRecord,
)


def detect_failure_modes(
    *,
    config: RunConfig,
    summary: RunSummary,
    trades: Sequence[TradeRecord],
    step_metrics: Sequence[StepMetric],
    epoch_summaries: Sequence[EpochSummary],
    cell_snapshots: Sequence[CellSnapshot],
) -> list[FailureModeObservation]:
    failures: list[FailureModeObservation] = []
    dead_volume_value = dead_volume_score(config, summary, epoch_summaries)
    oscillation_value = oscillation_score(epoch_summaries, cell_snapshots)
    concentration_by_epoch = top_k_cell_volume_share_by_epoch(cell_snapshots, k=1)

    if _dead_volume_equilibrium(config, summary, epoch_summaries):
        failures.append(
            FailureModeObservation(
                mode="dead_volume_equilibrium",
                severity="critical" if summary.num_trades == 0 else "warning",
                evidence=(
                    "Volume stayed low relative to initial TVL while the mechanism retained a hardened fee surface."
                ),
                trigger_heuristic="num_trades == 0 or dead_volume_score >= 1.1",
                evidence_fields={
                    "num_trades": summary.num_trades,
                    "dead_volume_score": dead_volume_value,
                },
            )
        )

    if _inactive_cell_pathology(config, cell_snapshots):
        failures.append(
            FailureModeObservation(
                mode="inactive_cell_pathology",
                severity="warning",
                evidence=(
                    "Low-activity Cells survived with little measured loss, which can make them look artificially fit."
                ),
                trigger_heuristic="more than half of final active Cells have negligible volume",
                evidence_fields={
                    "min_volume_threshold": config.min_volume_threshold,
                },
            )
        )

    if _lysis_cascade(config, epoch_summaries):
        failures.append(
            FailureModeObservation(
                mode="lysis_cascade",
                severity="critical",
                evidence="Many Cells were lysed or deactivated within a short epoch window.",
                trigger_heuristic="at least half of Cells lysed within one epoch window",
                evidence_fields={
                    "num_cells": config.num_cells,
                },
            )
        )

    if _gene_collapse_to_bounds(config, cell_snapshots):
        failures.append(
            FailureModeObservation(
                mode="gene_collapse_to_bounds",
                severity="warning",
                evidence="A large share of surviving gene values rapidly saturated configured bounds.",
                trigger_heuristic="at least half of early gene observations hit configured bounds",
                evidence_fields={
                    "final_gene_dispersion": final_gene_dispersion(cell_snapshots),
                },
            )
        )

    if _no_convergence_oscillation(epoch_summaries, cell_snapshots):
        failures.append(
            FailureModeObservation(
                mode="no_convergence_oscillation",
                severity="warning",
                evidence="Mean fitness and gene dispersion kept swinging rather than stabilizing.",
                trigger_heuristic="oscillation_score >= 2.0",
                evidence_fields={
                    "oscillation_score": oscillation_value,
                },
            )
        )

    if _monoculture_dominance(cell_snapshots):
        failures.append(
            FailureModeObservation(
                mode="monoculture_dominance",
                severity="warning",
                evidence="One Cell handled most volume for a sustained portion of the run.",
                trigger_heuristic="top-1 Cell volume share stayed >= 0.75 for much of the run",
                evidence_fields={
                    "top_1_share_final": concentration_by_epoch[max(concentration_by_epoch)] if concentration_by_epoch else 0.0,
                },
            )
        )

    if _oracle_fragility(config, summary):
        failures.append(
            FailureModeObservation(
                mode="oracle_fragility",
                severity="warning",
                evidence="A small amount of oracle lag or noise coincided with severe LP underperformance.",
                trigger_heuristic="oracle stress with LP underperformance and attributed loss > LP revenue",
                evidence_fields={
                    "oracle_mode": config.oracle_mode,
                    "oracle_lag_steps": config.oracle_lag_steps,
                },
            )
        )

    if step_metrics and all(metric.num_active_cells == 0 for metric in step_metrics[-max(1, len(step_metrics) // 5) :]):
        failures.append(
            FailureModeObservation(
                mode="all_cells_inactive_shutdown",
                severity="critical",
                evidence="The trailing portion of the run had no active Cells.",
                trigger_heuristic="all trailing-window step metrics show zero active Cells",
                evidence_fields={
                    "trailing_window": max(1, len(step_metrics) // 5),
                },
            )
        )

    return failures


def failure_mode_names(failure_modes: Sequence[FailureModeObservation]) -> list[str]:
    return [mode.mode for mode in failure_modes]


def _dead_volume_equilibrium(
    config: RunConfig,
    summary: RunSummary,
    epoch_summaries: Sequence[EpochSummary],
) -> bool:
    return summary.num_trades == 0 or dead_volume_score(config, summary, epoch_summaries) >= 1.1


def _inactive_cell_pathology(
    config: RunConfig,
    cell_snapshots: Sequence[CellSnapshot],
) -> bool:
    if not cell_snapshots:
        return False
    final_epoch = max(snapshot.epoch_index for snapshot in cell_snapshots)
    survivors = [snapshot for snapshot in cell_snapshots if snapshot.epoch_index == final_epoch and snapshot.active]
    if not survivors:
        return False
    threshold = max(config.min_volume_threshold, 1e-9)
    low_volume = sum(snapshot.epoch_volume_b <= threshold for snapshot in survivors)
    return low_volume / len(survivors) > 0.5


def _lysis_cascade(
    config: RunConfig,
    epoch_summaries: Sequence[EpochSummary],
) -> bool:
    if not epoch_summaries:
        return False
    cascade_threshold = max(2, config.num_cells // 2)
    return any(epoch.num_lysed_cells >= cascade_threshold for epoch in epoch_summaries)


def _gene_collapse_to_bounds(
    config: RunConfig,
    cell_snapshots: Sequence[CellSnapshot],
) -> bool:
    if not cell_snapshots:
        return False
    early_epoch = min(1, max(snapshot.epoch_index for snapshot in cell_snapshots))
    early_snapshots = [snapshot for snapshot in cell_snapshots if snapshot.epoch_index <= early_epoch]
    if not early_snapshots:
        return False

    tolerance = 1e-9
    hits = 0
    total = 0
    bounds = [
        ("f_min", config.f_min_min, config.f_min_max),
        ("mu", config.mu_min, config.mu_max),
        ("tau", config.tau_min, config.tau_max),
        ("beta", config.beta_min, config.beta_max),
    ]
    for snapshot in early_snapshots:
        for field_name, lower, upper in bounds:
            total += 1
            value = getattr(snapshot, field_name)
            if abs(value - lower) <= tolerance or abs(value - upper) <= tolerance:
                hits += 1
    return total > 0 and hits / total >= 0.5


def _no_convergence_oscillation(
    epoch_summaries: Sequence[EpochSummary],
    cell_snapshots: Sequence[CellSnapshot],
) -> bool:
    return oscillation_score(epoch_summaries, cell_snapshots) >= 2.0


def _monoculture_dominance(cell_snapshots: Sequence[CellSnapshot]) -> bool:
    shares = top_k_cell_volume_share_by_epoch(cell_snapshots, k=1)
    if not shares:
        return False
    sustained = [share for share in shares.values() if share >= 0.75]
    return len(sustained) >= max(1, len(shares) // 2)


def _oracle_fragility(config: RunConfig, summary: RunSummary) -> bool:
    oracle_stress = config.oracle_mode in {"lagged", "noisy"} or config.oracle_lag_steps > 0
    return oracle_stress and summary.lp_minus_hodl_b < 0 and summary.total_attributed_loss_b > summary.total_lp_revenue_b
