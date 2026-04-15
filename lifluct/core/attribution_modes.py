"""Offline attribution-mode comparisons for LIFLUCT trade logs."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Sequence

from lifluct.core.attribution import attributed_loss_b
from lifluct.core.fitness import compute_cell_fitness
from lifluct.types import CellSnapshot, RunConfig, StepMetric, TradeRecord


@dataclass(slots=True)
class AttributionModeResult:
    mode: str
    cell_loss_b: dict[int, float]
    cell_fitness: dict[int, float]
    loss_ranking: list[int]
    fitness_ranking: list[int]


def evaluate_attribution_modes(
    *,
    config: RunConfig,
    trades: Sequence[TradeRecord],
    step_metrics: Sequence[StepMetric],
    cell_snapshots: Sequence[CellSnapshot],
    modes: Sequence[str] | None = None,
) -> dict[str, AttributionModeResult]:
    selected_modes = list(
        modes
        or [
            "observed_spot",
            "lagged_observed",
            "twap",
            "delayed_reference",
            "research_ground_truth_proxy",
        ]
    )
    results: dict[str, AttributionModeResult] = {}
    for mode in selected_modes:
        losses = recompute_cell_attributed_loss(
            trades=trades,
            step_metrics=step_metrics,
            config=config,
            mode=mode,
        )
        fitness = recompute_final_epoch_fitness(
            cell_snapshots=cell_snapshots,
            recomputed_losses=losses,
            config=config,
        )
        results[mode] = AttributionModeResult(
            mode=mode,
            cell_loss_b=losses,
            cell_fitness=fitness,
            loss_ranking=rank_ids_by_value(losses, descending=True),
            fitness_ranking=rank_ids_by_value(fitness, descending=True),
        )
    return results


def recompute_cell_attributed_loss(
    *,
    trades: Sequence[TradeRecord],
    step_metrics: Sequence[StepMetric],
    config: RunConfig,
    mode: str,
) -> dict[int, float]:
    by_cell: dict[int, float] = {}
    for trade in trades:
        if trade.cell_id is None:
            continue
        reference_price = reference_price_for_trade(
            trade=trade,
            step_metrics=step_metrics,
            config=config,
            mode=mode,
        )
        loss_value = attributed_loss_b(
            exec_price=trade.exec_price,
            oracle_price=reference_price,
            volume_b=trade.notional_b,
            fee_rate=trade.fee_rate,
        )
        by_cell[trade.cell_id] = by_cell.get(trade.cell_id, 0.0) + loss_value
    return by_cell


def recompute_final_epoch_fitness(
    *,
    cell_snapshots: Sequence[CellSnapshot],
    recomputed_losses: dict[int, float],
    config: RunConfig,
) -> dict[int, float]:
    if not cell_snapshots:
        return {}
    final_epoch = max(snapshot.epoch_index for snapshot in cell_snapshots)
    fitness_map: dict[int, float] = {}
    for snapshot in cell_snapshots:
        if snapshot.epoch_index != final_epoch:
            continue
        proxy_cell = _snapshot_to_proxy(snapshot, recomputed_losses.get(snapshot.cell_id, 0.0))
        fitness_map[snapshot.cell_id] = compute_cell_fitness(proxy_cell, config)
    return fitness_map


def ranking_stability(
    attribution_results: dict[str, AttributionModeResult],
    *,
    reference_mode: str = "observed_spot",
) -> list[dict[str, float | str]]:
    reference = attribution_results.get(reference_mode)
    if reference is None:
        return []
    rows: list[dict[str, float | str]] = []
    for mode, result in attribution_results.items():
        rows.append(
            {
                "mode": mode,
                "loss_rank_correlation": spearman_rank_correlation(
                    reference.loss_ranking,
                    result.loss_ranking,
                ),
                "fitness_rank_correlation": spearman_rank_correlation(
                    reference.fitness_ranking,
                    result.fitness_ranking,
                ),
                "loss_pairwise_agreement": pairwise_ranking_agreement(
                    reference.loss_ranking,
                    result.loss_ranking,
                ),
                "fitness_pairwise_agreement": pairwise_ranking_agreement(
                    reference.fitness_ranking,
                    result.fitness_ranking,
                ),
                "fitness_top_1_overlap": top_k_overlap(
                    reference.fitness_ranking,
                    result.fitness_ranking,
                    k=1,
                ),
                "fitness_top_2_overlap": top_k_overlap(
                    reference.fitness_ranking,
                    result.fitness_ranking,
                    k=2,
                ),
                "fitness_bottom_1_overlap": bottom_k_overlap(
                    reference.fitness_ranking,
                    result.fitness_ranking,
                    k=1,
                ),
                "fitness_bottom_2_overlap": bottom_k_overlap(
                    reference.fitness_ranking,
                    result.fitness_ranking,
                    k=2,
                ),
                "loss_top_1_overlap": top_k_overlap(
                    reference.loss_ranking,
                    result.loss_ranking,
                    k=1,
                ),
                "loss_top_2_overlap": top_k_overlap(
                    reference.loss_ranking,
                    result.loss_ranking,
                    k=2,
                ),
                "loss_bottom_1_overlap": bottom_k_overlap(
                    reference.loss_ranking,
                    result.loss_ranking,
                    k=1,
                ),
                "loss_bottom_2_overlap": bottom_k_overlap(
                    reference.loss_ranking,
                    result.loss_ranking,
                    k=2,
                ),
            }
        )
    return rows


def reference_price_for_trade(
    *,
    trade: TradeRecord,
    step_metrics: Sequence[StepMetric],
    config: RunConfig,
    mode: str,
) -> float:
    metrics = {metric.step: metric for metric in step_metrics}
    if not metrics:
        return trade.oracle_price
    max_step = max(metrics)
    step = min(max(trade.step, 0), max_step)

    if mode == "observed_spot":
        return metrics[step].observed_price
    if mode == "lagged_observed":
        lagged_step = max(0, step - max(1, config.attribution_lag_steps))
        return metrics[lagged_step].observed_price
    if mode == "twap":
        window = max(1, config.attribution_twap_window)
        start = max(0, step - window + 1)
        prices = [metrics[current_step].observed_price for current_step in range(start, step + 1)]
        return statistics.fmean(prices)
    if mode == "delayed_reference":
        delayed_step = min(max_step, step + max(1, config.delayed_reference_steps))
        return metrics[delayed_step].observed_price
    if mode == "research_ground_truth_proxy":
        horizon = max(1, config.research_future_horizon)
        end = min(max_step, step + horizon)
        prices = [metrics[current_step].true_price for current_step in range(step, end + 1)]
        return statistics.fmean(prices)
    raise ValueError(f"unsupported attribution mode: {mode}")


def rank_ids_by_value(values: dict[int, float], *, descending: bool) -> list[int]:
    return [
        cell_id
        for cell_id, _ in sorted(
            values.items(),
            key=lambda item: (item[1], -item[0]) if descending else (-item[1], item[0]),
            reverse=descending,
        )
    ]


def spearman_rank_correlation(first_ranking: Sequence[int], second_ranking: Sequence[int]) -> float:
    universe = sorted(set(first_ranking) | set(second_ranking))
    if len(universe) <= 1:
        return 1.0

    first_map = _rank_map(first_ranking, universe)
    second_map = _rank_map(second_ranking, universe)
    first_values = [first_map[cell_id] for cell_id in universe]
    second_values = [second_map[cell_id] for cell_id in universe]
    mean_first = statistics.fmean(first_values)
    mean_second = statistics.fmean(second_values)
    covariance = sum(
        (first - mean_first) * (second - mean_second)
        for first, second in zip(first_values, second_values, strict=True)
    )
    variance_first = sum((value - mean_first) ** 2 for value in first_values)
    variance_second = sum((value - mean_second) ** 2 for value in second_values)
    if variance_first <= 0.0 or variance_second <= 0.0:
        return 1.0
    return covariance / math.sqrt(variance_first * variance_second)


def pairwise_ranking_agreement(first_ranking: Sequence[int], second_ranking: Sequence[int]) -> float:
    universe = sorted(set(first_ranking) | set(second_ranking))
    if len(universe) <= 1:
        return 1.0

    first_map = _rank_map(first_ranking, universe)
    second_map = _rank_map(second_ranking, universe)
    total_pairs = 0
    agreeing_pairs = 0
    for index, left in enumerate(universe):
        for right in universe[index + 1 :]:
            total_pairs += 1
            first_order = first_map[left] <= first_map[right]
            second_order = second_map[left] <= second_map[right]
            if first_order == second_order:
                agreeing_pairs += 1
    if total_pairs == 0:
        return 1.0
    return agreeing_pairs / total_pairs


def top_k_overlap(first_ranking: Sequence[int], second_ranking: Sequence[int], *, k: int) -> float:
    if k <= 0:
        return 0.0
    first = set(first_ranking[:k])
    second = set(second_ranking[:k])
    universe = max(len(first), len(second), 1)
    return len(first & second) / universe


def bottom_k_overlap(first_ranking: Sequence[int], second_ranking: Sequence[int], *, k: int) -> float:
    if k <= 0:
        return 0.0
    first = set(first_ranking[-k:])
    second = set(second_ranking[-k:])
    universe = max(len(first), len(second), 1)
    return len(first & second) / universe


def _rank_map(ranking: Sequence[int], universe: Sequence[int]) -> dict[int, float]:
    default_rank = float(len(universe))
    return {cell_id: float(ranking.index(cell_id)) if cell_id in ranking else default_rank for cell_id in universe}


def _snapshot_to_proxy(snapshot: CellSnapshot, recomputed_loss: float) -> Any:
    """
    Build a minimal object compatible with `compute_cell_fitness`.

    This is intentionally light-weight because Phase 4 only needs offline
    fitness comparison under alternative attribution references.
    """

    class _ProxyCell:
        epoch_lp_revenue_b = snapshot.epoch_lp_revenue_b
        epoch_attributed_loss_b = recomputed_loss
        epoch_volume_b = snapshot.epoch_volume_b
        epoch_trader_cost_b = snapshot.epoch_trader_cost_b

    return _ProxyCell()
