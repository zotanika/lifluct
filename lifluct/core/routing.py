"""Routing policies for user and toxic flow in the multi-cell simulator."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from lifluct.core.cell import CellState


def choose_user_cell(
    cells: Iterable[CellState],
    routing_mode: str,
    current_fee_map: dict[int, float],
    rng: np.random.Generator,
    *,
    p_best: float = 0.8,
) -> CellState | None:
    active_cells = [cell for cell in cells if cell.active]
    if not active_cells:
        return None

    if routing_mode == "weighted_random":
        return _choose_weighted_random(active_cells, rng)
    if routing_mode == "cheapest_fee":
        return _choose_cheapest(active_cells, current_fee_map)
    if routing_mode == "noisy_best":
        if rng.random() < p_best:
            return _choose_cheapest(active_cells, current_fee_map)
        return _choose_weighted_random(active_cells, rng)
    raise ValueError(f"unsupported user routing mode: {routing_mode}")


def choose_toxic_cell(
    cells: Iterable[CellState],
    routing_mode: str,
    current_fee_map: dict[int, float],
    rng: np.random.Generator,
) -> CellState | None:
    """
    Choose the Cell for adversarial / toxic flow.

    Toxic routing is intentionally adversarial by design: it looks for the weakest
    currently active quoting surface exposed by the shared Cluster.
    """
    active_cells = [cell for cell in cells if cell.active]
    if not active_cells:
        return None

    if routing_mode in {"cheapest_active", "max_extraction_placeholder"}:
        return _choose_cheapest(active_cells, current_fee_map)
    raise ValueError(f"unsupported toxic routing mode: {routing_mode}")


def _choose_weighted_random(cells: list[CellState], rng: np.random.Generator) -> CellState:
    weights = np.array([max(0.0, cell.current_user_routing_weight()) for cell in cells], dtype=float)
    if float(weights.sum()) <= 0.0:
        weights = np.ones(len(cells), dtype=float)
    probabilities = weights / weights.sum()
    selected_index = int(rng.choice(len(cells), p=probabilities))
    return cells[selected_index]


def _choose_cheapest(cells: list[CellState], current_fee_map: dict[int, float]) -> CellState:
    return min(cells, key=lambda cell: (current_fee_map[cell.cell_id], cell.cell_id))
