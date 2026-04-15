"""Stronger adversary heuristics for Phase 4 evaluation."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from lifluct.core.cell import CellState
from lifluct.core.cluster import pool_price, tvl
from lifluct.types import ClusterState, OracleState, RunConfig


def effective_toxic_mode(config: RunConfig) -> str:
    return config.toxic_mode or config.toxic_routing_mode


def toxic_flow_probability(config: RunConfig, step: int) -> float:
    mode = effective_toxic_mode(config)
    if mode == "burst_toxicity" and in_burst_window(config, step):
        return config.toxic_burst_probability
    return config.toxic_trade_probability


def in_burst_window(config: RunConfig, step: int) -> bool:
    if config.toxic_burst_end_step <= config.toxic_burst_start_step:
        return False
    return config.toxic_burst_start_step <= step <= config.toxic_burst_end_step


def choose_adversarial_cell(
    *,
    cells: Iterable[CellState],
    current_fee_map: dict[int, float],
    rng: np.random.Generator,
    config: RunConfig,
    state: ClusterState,
    oracle_state: OracleState,
) -> CellState | None:
    active_cells = [cell for cell in cells if cell.active]
    if not active_cells:
        return None

    mode = effective_toxic_mode(config)
    if mode == "cheapest_active":
        return min(active_cells, key=lambda cell: (current_fee_map[cell.cell_id], cell.cell_id))
    if mode == "fee_aware_max_extraction":
        return max(
            active_cells,
            key=lambda cell: (
                estimated_net_extraction(
                    state=state,
                    oracle_state=oracle_state,
                    fee_rate=current_fee_map[cell.cell_id],
                ),
                -cell.cell_id,
            ),
        )
    if mode == "sabotage_targeted_cell":
        target = choose_sabotage_target(
            active_cells=active_cells,
            current_fee_map=current_fee_map,
            config=config,
        )
        return target or min(active_cells, key=lambda cell: (current_fee_map[cell.cell_id], cell.cell_id))
    if mode == "burst_toxicity":
        # During bursts, reuse the extraction-aware heuristic; outside bursts the
        # probability schedule already reduces toxic flow to the base rate.
        return max(
            active_cells,
            key=lambda cell: (
                estimated_net_extraction(
                    state=state,
                    oracle_state=oracle_state,
                    fee_rate=current_fee_map[cell.cell_id],
                ),
                -cell.cell_id,
            ),
        )
    if mode == "max_extraction_placeholder":
        return min(active_cells, key=lambda cell: (current_fee_map[cell.cell_id], cell.cell_id))
    raise ValueError(f"unsupported toxic mode: {mode}")


def estimated_net_extraction(
    *,
    state: ClusterState,
    oracle_state: OracleState,
    fee_rate: float,
) -> float:
    """
    Stylized net-extraction score for adversarial routing.

    Under the current shared-Cluster CPMM model, the main per-Cell difference is
    still fee level, so this approximation often reduces to "choose the lowest
    effective fee". It is intentionally labeled as heuristic rather than exact.
    """
    deviation_value = abs(pool_price(state) / oracle_state.true_price - 1.0)
    local_tvl = tvl(state, oracle_state.true_price)
    gross_opportunity = deviation_value * local_tvl
    return gross_opportunity * max(0.0, 1.0 - fee_rate)


def choose_sabotage_target(
    *,
    active_cells: list[CellState],
    current_fee_map: dict[int, float],
    config: RunConfig,
) -> CellState | None:
    if config.sabotage_target_cell_mode == "fixed_id" and config.sabotage_target_cell_id >= 0:
        for cell in active_cells:
            if cell.cell_id == config.sabotage_target_cell_id:
                return cell
        return None
    if config.sabotage_target_cell_mode == "cheapest_fee":
        return min(active_cells, key=lambda cell: (current_fee_map[cell.cell_id], cell.cell_id))
    if config.sabotage_target_cell_mode == "weakest_fitness":
        return min(
            active_cells,
            key=lambda cell: (
                cell.rolling_fitness_mean if cell.rolling_fitness_mean is not None else _current_weakness_score(cell),
                cell.cell_id,
            ),
        )
    raise ValueError(f"unsupported sabotage target mode: {config.sabotage_target_cell_mode}")


def _current_weakness_score(cell: CellState) -> float:
    return cell.epoch_lp_revenue_b - cell.epoch_attributed_loss_b
