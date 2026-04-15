from lifluct.core.cell import CellGenes, CellState
from lifluct.core.fitness import compute_cell_fitness
from lifluct.types import RunConfig


def _config(**updates: object) -> RunConfig:
    raw = {
        "seed": 1,
        "num_steps": 10,
        "initial_reserve_a": 1000.0,
        "initial_reserve_b": 100000.0,
        "initial_price": 100.0,
        "sigma": 0.02,
        "q_trade": 0.3,
        "max_trade_fraction_of_tvl": 0.02,
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
        "fitness_mode": "basic_normalized",
        "fitness_lambda": 1.0,
        "fitness_gamma": 1.0,
        "fitness_omega": 1.0,
        "min_volume_threshold": 1000.0,
        "inactivity_penalty": 0.5,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def _cell(loss: float, volume: float = 1000.0) -> CellState:
    cell = CellState(
        cell_id=0,
        active=True,
        lysis_triggered=False,
        generation_index=0,
        parent_cell_id=None,
        genes=CellGenes(0.003, 0.1, 0.002, 0.1),
    )
    cell.epoch_volume_b = volume
    cell.epoch_lp_revenue_b = 20.0
    cell.epoch_trader_cost_b = 8.0
    cell.epoch_attributed_loss_b = loss
    return cell


def test_higher_attributed_loss_reduces_fitness() -> None:
    config = _config(fitness_mode="basic_normalized")
    safer_cell = _cell(loss=5.0)
    leakier_cell = _cell(loss=10.0)

    assert compute_cell_fitness(safer_cell, config) > compute_cell_fitness(leakier_cell, config)


def test_inactivity_penalty_works() -> None:
    config = _config(fitness_mode="full_with_inactivity_penalty")
    active_cell = _cell(loss=5.0, volume=2_000.0)
    inactive_cell = _cell(loss=5.0, volume=100.0)

    assert compute_cell_fitness(active_cell, config) > compute_cell_fitness(inactive_cell, config)
