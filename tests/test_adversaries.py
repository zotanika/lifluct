import numpy as np

from lifluct.core.adversaries import (
    choose_adversarial_cell,
    choose_sabotage_target,
    toxic_flow_probability,
)
from lifluct.core.cell import CellGenes, CellState
from lifluct.types import ClusterState, OracleState, RunConfig


def _config(**updates: object) -> RunConfig:
    raw = {
        "seed": 1,
        "num_steps": 20,
        "initial_reserve_a": 1000.0,
        "initial_reserve_b": 100000.0,
        "initial_price": 100.0,
        "sigma": 0.02,
        "q_trade": 0.35,
        "max_trade_fraction_of_tvl": 0.01,
        "arbitrage_threshold": 0.001,
        "baseline_type": "lifluct_multi_cell",
        "f_min": 0.003,
        "mu": 0.15,
        "tau": 0.002,
        "s_base": 0.9,
        "beta": 0.2,
        "tvl_target": 200000.0,
        "oracle_mode": "perfect",
        "oracle_lag_steps": 0,
        "use_dynamic_fee": True,
        "use_turgor": True,
        "num_cells": 3,
        "toxic_mode": "cheapest_active",
        "toxic_trade_probability": 0.2,
        "toxic_burst_probability": 0.9,
        "toxic_burst_start_step": 5,
        "toxic_burst_end_step": 10,
        "sabotage_target_cell_mode": "fixed_id",
        "sabotage_target_cell_id": 1,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def _cells() -> list[CellState]:
    return [
        CellState(0, True, False, 0, None, CellGenes(0.003, 0.1, 0.002, 0.1)),
        CellState(1, True, False, 0, None, CellGenes(0.003, 0.1, 0.002, 0.1)),
        CellState(2, False, False, 0, None, CellGenes(0.003, 0.1, 0.002, 0.1)),
    ]


def test_cheapest_active_adversary_chooses_minimum_fee_active_cell() -> None:
    config = _config(toxic_mode="cheapest_active")
    chosen = choose_adversarial_cell(
        cells=_cells(),
        current_fee_map={0: 0.01, 1: 0.005},
        rng=np.random.default_rng(1),
        config=config,
        state=ClusterState(1000.0, 100000.0),
        oracle_state=OracleState(100.0, 100.0, 0),
    )

    assert chosen is not None
    assert chosen.cell_id == 1


def test_sabotage_mode_can_target_specific_cell() -> None:
    cells = _cells()
    target = choose_sabotage_target(
        active_cells=[cell for cell in cells if cell.active],
        current_fee_map={0: 0.01, 1: 0.005},
        config=_config(toxic_mode="sabotage_targeted_cell", sabotage_target_cell_id=1),
    )

    assert target is not None
    assert target.cell_id == 1


def test_burst_mode_changes_toxic_flow_probability_over_time() -> None:
    config = _config(toxic_mode="burst_toxicity")

    assert toxic_flow_probability(config, 3) == 0.2
    assert toxic_flow_probability(config, 6) == 0.9
