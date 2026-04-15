"""Validation and failure-mode heuristics for LIFLUCT research runs."""

from __future__ import annotations

import math
import statistics
from typing import Any, Mapping, Sequence

from lifluct.core.diagnostics import dead_volume_score, gene_variance_by_epoch, top_k_cell_volume_share_by_epoch
from lifluct.core.failure_modes import detect_failure_modes
from lifluct.types import (
    CellSnapshot,
    EpochSummary,
    FailureModeObservation,
    RunConfig,
    RunSummary,
    SimulationResult,
    StepMetric,
    TradeRecord,
    ValidationWarning,
)


def validate_result(
    result: SimulationResult,
) -> tuple[list[ValidationWarning], list[FailureModeObservation]]:
    return _validate_components(
        config=result.config,
        summary=result.summary,
        trades=result.trades,
        step_metrics=result.step_metrics,
        epoch_summaries=result.epoch_summaries,
        cell_snapshots=result.cell_snapshots,
    )


def validate_loaded_run(
    data: Mapping[str, Any],
) -> tuple[list[ValidationWarning], list[FailureModeObservation]]:
    return _validate_components(
        config=data["config"],
        summary=data["summary"],
        trades=data.get("trades", []),
        step_metrics=data.get("step_metrics", []),
        epoch_summaries=data.get("epoch_summaries", []),
        cell_snapshots=data.get("cell_snapshots", []),
    )


def _validate_components(
    *,
    config: RunConfig,
    summary: RunSummary,
    trades: Sequence[TradeRecord],
    step_metrics: Sequence[StepMetric],
    epoch_summaries: Sequence[EpochSummary],
    cell_snapshots: Sequence[CellSnapshot],
) -> tuple[list[ValidationWarning], list[FailureModeObservation]]:
    warnings: list[ValidationWarning] = []
    failure_modes: list[FailureModeObservation] = []

    if summary.num_trades == 0:
        warnings.append(
            ValidationWarning(
                code="no_trades",
                severity="high",
                message="Run produced no trades, so mechanism conclusions are not meaningful.",
            )
        )

    early_cutoff = max(1, config.num_steps // 4)
    early_zero_active = [
        metric.step
        for metric in step_metrics
        if metric.step <= early_cutoff and metric.num_active_cells == 0
    ]
    if early_zero_active:
        warnings.append(
            ValidationWarning(
                code="all_cells_inactive_early",
                severity="high",
                message=(
                    "All Cells became inactive unusually early in the run "
                    f"(first observed at step {early_zero_active[0]})."
                ),
            )
        )

    early_trades = list(trades[: max(1, min(10, len(trades)))])
    if early_trades:
        avg_early_fee = statistics.fmean(trade.fee_rate for trade in early_trades)
        if avg_early_fee >= 0.9 * config.fee_max_global:
            warnings.append(
                ValidationWarning(
                    code="fees_near_max_early",
                    severity="medium",
                    message=(
                        "Average fee in the earliest trades was near the configured fee cap, "
                        "which may indicate over-hardening or an unstable setup."
                    ),
                )
            )

    if cell_snapshots and _genes_collapsed_to_bounds_quickly(cell_snapshots, config):
        warnings.append(
            ValidationWarning(
                code="genes_collapsed_to_bounds_quickly",
                severity="medium",
                message=(
                    "A large share of gene values hit configured bounds very early, "
                    "which may indicate mutation or selection settings that are too aggressive."
                ),
            )
        )

    if trades and all(abs(trade.attributed_loss_b) <= config.epsilon for trade in trades):
        warnings.append(
            ValidationWarning(
                code="attributed_loss_always_zero",
                severity="medium",
                message="Attributed loss stayed at zero for all trades.",
            )
        )

    if trades and all(abs(trade.trader_cost_b) <= config.epsilon for trade in trades):
        warnings.append(
            ValidationWarning(
                code="trader_cost_always_zero",
                severity="medium",
                message="Trader cost proxy stayed at zero for all trades.",
            )
        )

    if _has_invalid_state(step_metrics):
        warnings.append(
            ValidationWarning(
                code="invalid_state_detected",
                severity="high",
                message="Run produced a non-finite value, non-positive reserve, or impossible LP state.",
            )
        )

    if epoch_summaries and epoch_summaries[-1].mean_fitness < -0.05:
        warnings.append(
            ValidationWarning(
                code="final_mean_fitness_strongly_negative",
                severity="medium",
                message=(
                    "Final mean fitness was strongly negative, which suggests the mechanism ended in an unhealthy state."
                ),
            )
        )

    if summary.total_dead_cells >= max(config.num_cells, max(1, len(epoch_summaries)) * max(1, config.num_cells // 2)):
        warnings.append(
            ValidationWarning(
                code="very_high_death_count",
                severity="medium",
                message="Cell death count was very high relative to the configured population size.",
            )
        )

    if summary.total_attributed_loss_b > 3.0 * max(summary.total_lp_revenue_b, config.epsilon):
        warnings.append(
            ValidationWarning(
                code="loss_overwhelms_lp_revenue",
                severity="high",
                message="Attributed loss was much larger than LP revenue.",
            )
        )

    if step_metrics and step_metrics[-1].num_active_cells <= max(0, min(1, config.num_cells - 1)):
        warnings.append(
            ValidationWarning(
                code="all_or_nearly_all_cells_inactive",
                severity="high",
                message="The run finished with all or nearly all Cells inactive.",
            )
        )

    if dead_volume_score(config, summary, epoch_summaries) >= 1.1:
        warnings.append(
            ValidationWarning(
                code="volume_collapse",
                severity="medium",
                message="Volume appears to have collapsed relative to the size of the market state.",
            )
        )

    top_1_shares = top_k_cell_volume_share_by_epoch(cell_snapshots, k=1)
    if top_1_shares and max(top_1_shares.values()) >= 0.85:
        warnings.append(
            ValidationWarning(
                code="one_cell_dominance",
                severity="medium",
                message="One Cell dominated the majority of volume for at least part of the run.",
            )
        )

    if trades and all(abs(trade.trader_cost_b) <= max(config.epsilon, 1e-9) for trade in trades) and _has_adversarial_pressure(config):
        warnings.append(
            ValidationWarning(
                code="suspicious_near_zero_trader_cost",
                severity="medium",
                message="Trader cost stayed near zero even though adversarial flow was enabled.",
            )
        )

    if trades and all(abs(trade.attributed_loss_b) <= max(config.epsilon, 1e-9) for trade in trades) and _has_adversarial_pressure(config):
        warnings.append(
            ValidationWarning(
                code="suspicious_zero_attributed_loss_under_adversary",
                severity="medium",
                message="Attributed loss stayed near zero despite adversarial settings.",
            )
        )

    failure_modes.extend(
        detect_failure_modes(
            config=config,
            summary=summary,
            trades=trades,
            step_metrics=step_metrics,
            epoch_summaries=epoch_summaries,
            cell_snapshots=cell_snapshots,
        )
    )
    return warnings, failure_modes


def _genes_collapsed_to_bounds_quickly(
    cell_snapshots: Sequence[CellSnapshot],
    config: RunConfig,
) -> bool:
    early_epoch_limit = min(1, max(snapshot.epoch_index for snapshot in cell_snapshots))
    early_snapshots = [snapshot for snapshot in cell_snapshots if snapshot.epoch_index <= early_epoch_limit]
    if not early_snapshots:
        return False

    tolerance = 1e-9
    boundary_hits = 0
    total_checks = 0
    bounds = [
        ("f_min", config.f_min_min, config.f_min_max),
        ("mu", config.mu_min, config.mu_max),
        ("tau", config.tau_min, config.tau_max),
        ("beta", config.beta_min, config.beta_max),
    ]
    for snapshot in early_snapshots:
        for field_name, lower, upper in bounds:
            total_checks += 1
            value = getattr(snapshot, field_name)
            if abs(value - lower) <= tolerance or abs(value - upper) <= tolerance:
                boundary_hits += 1
    return total_checks > 0 and (boundary_hits / total_checks) >= 0.5


def _has_invalid_state(step_metrics: Sequence[StepMetric]) -> bool:
    for metric in step_metrics:
        values = [
            metric.true_price,
            metric.observed_price,
            metric.pool_price,
            metric.reserve_a,
            metric.reserve_b,
            metric.tvl_b,
            metric.lp_value_b,
            metric.hodl_value_b,
        ]
        if any((not math.isfinite(value)) for value in values):
            return True
        if metric.reserve_a <= 0 or metric.reserve_b <= 0:
            return True
    return False


def _has_adversarial_pressure(config: RunConfig) -> bool:
    return (
        config.toxic_trade_probability > 0.0
        or config.num_toxic_attempts_per_step > 0
        or (config.toxic_mode not in {"", "cheapest_active"})
    )
