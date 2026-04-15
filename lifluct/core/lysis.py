"""Heuristic intra-epoch lysis logic for Phase 2."""

from __future__ import annotations

from lifluct.core.cell import CellState


def should_lyse(cell_state: CellState, kappa: float) -> bool:
    return cell_state.epoch_attributed_loss_b > kappa * cell_state.epoch_fees_total_b


def apply_lysis(
    cell_state: CellState,
    *,
    lysis_mode: str,
    soft_penalty: float,
) -> None:
    """
    Apply heuristic lysis state changes.

    This is intentionally a coarse circuit-breaker approximation and can create
    false positives, especially under stale or noisy oracle observations.
    """
    if lysis_mode == "off" or cell_state.lysis_triggered:
        return

    cell_state.lysis_triggered = True
    cell_state.lifetime_lysis_count += 1
    if lysis_mode == "soft":
        cell_state.routing_weight_multiplier *= soft_penalty
        return
    if lysis_mode == "hard":
        cell_state.active = False
        return
    raise ValueError(f"unsupported lysis mode: {lysis_mode}")
