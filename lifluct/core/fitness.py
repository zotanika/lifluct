"""Fitness scoring for multi-cell LIFLUCT simulations."""

from __future__ import annotations

from lifluct.core.cell import CellState
from lifluct.types import RunConfig


def basic_normalized(cell: CellState, *, omega: float, epsilon: float) -> float:
    return (cell.epoch_lp_revenue_b - omega * cell.epoch_attributed_loss_b) / (
        cell.epoch_volume_b + epsilon
    )


def full_balanced(
    cell: CellState,
    *,
    lambda_weight: float,
    gamma: float,
    omega: float,
    epsilon: float,
) -> float:
    volume = cell.epoch_volume_b + epsilon
    return (
        lambda_weight * (cell.epoch_lp_revenue_b / volume)
        - gamma * (cell.epoch_trader_cost_b / volume)
        - omega * (cell.epoch_attributed_loss_b / volume)
    )


def full_with_inactivity_penalty(
    cell: CellState,
    *,
    lambda_weight: float,
    gamma: float,
    omega: float,
    epsilon: float,
    min_volume_threshold: float,
    inactivity_penalty: float,
) -> float:
    """
    Penalize cells that avoid loss only by doing almost nothing.

    The PRD explicitly calls out inactive-cell pathologies, so this mode discourages
    zero-volume strategies from looking artificially safe.
    """
    score = full_balanced(
        cell,
        lambda_weight=lambda_weight,
        gamma=gamma,
        omega=omega,
        epsilon=epsilon,
    )
    if cell.epoch_volume_b < min_volume_threshold:
        score -= inactivity_penalty
    return score


def compute_cell_fitness(cell: CellState, config: RunConfig) -> float:
    if config.fitness_mode == "basic_normalized":
        return basic_normalized(
            cell,
            omega=config.fitness_omega,
            epsilon=config.epsilon,
        )
    if config.fitness_mode == "full_balanced":
        return full_balanced(
            cell,
            lambda_weight=config.fitness_lambda,
            gamma=config.fitness_gamma,
            omega=config.fitness_omega,
            epsilon=config.epsilon,
        )
    if config.fitness_mode == "full_with_inactivity_penalty":
        return full_with_inactivity_penalty(
            cell,
            lambda_weight=config.fitness_lambda,
            gamma=config.fitness_gamma,
            omega=config.fitness_omega,
            epsilon=config.epsilon,
            min_volume_threshold=config.min_volume_threshold,
            inactivity_penalty=config.inactivity_penalty,
        )
    raise ValueError(f"unsupported fitness mode: {config.fitness_mode}")
