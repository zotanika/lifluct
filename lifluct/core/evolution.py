"""Epoch-end evolutionary selection for LIFLUCT Cells."""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from lifluct.core.cell import CellGenes, CellState
from lifluct.core.fitness import compute_cell_fitness
from lifluct.types import RunConfig


def compute_fitness_for_cells(cells: list[CellState], config: RunConfig) -> dict[int, float]:
    return {cell.cell_id: compute_cell_fitness(cell, config) for cell in cells}


def rank_cells(cells: list[CellState], fitness_map: dict[int, float]) -> list[CellState]:
    return sorted(
        cells,
        key=lambda cell: (
            fitness_map[cell.cell_id],
            cell.epoch_volume_b,
            cell.epoch_lp_revenue_b,
            -cell.cell_id,
        ),
        reverse=True,
    )


def select_survivors(
    cells: list[CellState],
    fitness_map: dict[int, float],
    selection_fraction: float,
    elite_count: int,
) -> tuple[list[CellState], list[CellState]]:
    ranked_cells = rank_cells(cells, fitness_map)
    keep_count = max(1, int(round(len(cells) * selection_fraction)))
    keep_count = max(keep_count, elite_count)
    keep_count = min(len(cells), keep_count)
    return ranked_cells[:keep_count], ranked_cells[keep_count:]


def mutate_genes(
    genes: CellGenes,
    config: RunConfig,
    rng: np.random.Generator,
) -> CellGenes:
    if config.mutation_mode == "multiplicative_gaussian":
        mutated = CellGenes(
            f_min=genes.f_min * math.exp(rng.normal(0.0, config.mutation_sigma_f_min)),
            mu=genes.mu * math.exp(rng.normal(0.0, config.mutation_sigma_mu)),
            tau=genes.tau * math.exp(rng.normal(0.0, config.mutation_sigma_tau)),
            beta=genes.beta * math.exp(rng.normal(0.0, config.mutation_sigma_beta)),
        )
    elif config.mutation_mode == "additive_gaussian":
        mutated = CellGenes(
            f_min=genes.f_min + rng.normal(0.0, config.mutation_sigma_f_min),
            mu=genes.mu + rng.normal(0.0, config.mutation_sigma_mu),
            tau=genes.tau + rng.normal(0.0, config.mutation_sigma_tau),
            beta=genes.beta + rng.normal(0.0, config.mutation_sigma_beta),
        )
    else:
        raise ValueError(f"unsupported mutation mode: {config.mutation_mode}")

    return CellGenes(
        f_min=float(min(config.f_min_max, max(config.f_min_min, mutated.f_min))),
        mu=float(min(config.mu_max, max(config.mu_min, mutated.mu))),
        tau=float(min(config.tau_max, max(config.tau_min, mutated.tau))),
        beta=float(min(config.beta_max, max(config.beta_min, mutated.beta))),
    )


def spawn_offspring(
    survivors: list[CellState],
    dead_cells: list[CellState],
    fitness_map: dict[int, float],
    config: RunConfig,
    rng: np.random.Generator,
) -> list[CellState]:
    offspring: list[CellState] = []
    for dead_cell in dead_cells:
        parent = _choose_parent(survivors, fitness_map, config.parent_selection_mode, rng)
        child_genes = mutate_genes(parent.genes, config, rng)
        offspring.append(
            CellState(
                cell_id=dead_cell.cell_id,
                active=True,
                lysis_triggered=False,
                generation_index=parent.generation_index + 1,
                parent_cell_id=parent.cell_id,
                genes=child_genes,
                weight_user_routing=1.0,
            )
        )
    return offspring


def advance_generation(
    cells: list[CellState],
    config: RunConfig,
    rng: np.random.Generator,
) -> tuple[list[CellState], dict[int, float], list[CellState], list[CellState]]:
    fitness_map = compute_fitness_for_cells(cells, config)
    survivors, dead_cells = select_survivors(
        cells,
        fitness_map,
        selection_fraction=config.selection_fraction,
        elite_count=config.elite_count,
    )
    for cell in dead_cells:
        cell.lifetime_death_count += 1

    survivor_copies: list[CellState] = [replace(cell) for cell in survivors]
    for cell in survivor_copies:
        _update_rolling_fitness(cell, fitness_map[cell.cell_id])
        cell.reset_epoch_stats()

    offspring = spawn_offspring(survivor_copies, dead_cells, fitness_map, config, rng)
    new_population = sorted([*survivor_copies, *offspring], key=lambda cell: cell.cell_id)
    return new_population, fitness_map, survivors, dead_cells


def _choose_parent(
    survivors: list[CellState],
    fitness_map: dict[int, float],
    parent_selection_mode: str,
    rng: np.random.Generator,
) -> CellState:
    if parent_selection_mode == "uniform":
        return survivors[int(rng.integers(0, len(survivors)))]
    if parent_selection_mode == "weighted_by_fitness":
        scores = np.array([fitness_map[cell.cell_id] for cell in survivors], dtype=float)
        scores -= scores.min()
        scores += 1e-9
        probabilities = scores / scores.sum()
        return survivors[int(rng.choice(len(survivors), p=probabilities))]
    raise ValueError(f"unsupported parent selection mode: {parent_selection_mode}")


def _update_rolling_fitness(cell: CellState, fitness: float) -> None:
    if cell.rolling_fitness_mean is None or cell.rolling_fitness_std is None:
        cell.rolling_fitness_mean = fitness
        cell.rolling_fitness_std = 0.0
        return
    new_mean = 0.5 * cell.rolling_fitness_mean + 0.5 * fitness
    new_var = 0.5 * (cell.rolling_fitness_std ** 2) + 0.5 * ((fitness - new_mean) ** 2)
    cell.rolling_fitness_mean = new_mean
    cell.rolling_fitness_std = math.sqrt(max(0.0, new_var))
