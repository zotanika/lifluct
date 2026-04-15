import numpy as np

from lifluct.core.cell import CellGenes, CellState
from lifluct.core.evolution import advance_generation, compute_fitness_for_cells, select_survivors
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
        "fitness_omega": 1.0,
        "selection_fraction": 0.5,
        "elite_count": 1,
        "mutation_mode": "multiplicative_gaussian",
        "mutation_sigma_f_min": 0.1,
        "mutation_sigma_mu": 0.1,
        "mutation_sigma_tau": 0.1,
        "mutation_sigma_beta": 0.1,
        "f_min_min": 0.0005,
        "f_min_max": 0.01,
        "mu_min": 0.0,
        "mu_max": 25.0,
        "tau_min": 0.0001,
        "tau_max": 0.02,
        "beta_min": 0.0,
        "beta_max": 5.0,
        "parent_selection_mode": "uniform",
        "enable_evolution": True,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def _cells() -> list[CellState]:
    cells = []
    for cell_id, revenue in enumerate([10.0, 8.0, 2.0, 1.0]):
        cell = CellState(
            cell_id=cell_id,
            active=True,
            lysis_triggered=False,
            generation_index=0,
            parent_cell_id=None,
            genes=CellGenes(0.003, 0.1 + cell_id, 0.002, 0.1),
        )
        cell.epoch_volume_b = 1000.0
        cell.epoch_lp_revenue_b = revenue
        cell.epoch_attributed_loss_b = 0.0
        cells.append(cell)
    return cells


def test_top_fraction_survives() -> None:
    config = _config()
    cells = _cells()
    fitness_map = compute_fitness_for_cells(cells, config)
    survivors, dead_cells = select_survivors(cells, fitness_map, 0.5, 1)

    assert {cell.cell_id for cell in survivors} == {0, 1}
    assert {cell.cell_id for cell in dead_cells} == {2, 3}


def test_offspring_stay_inside_gene_bounds_and_track_parent() -> None:
    config = _config()
    cells = _cells()
    rng = np.random.default_rng(123)

    new_population, _, survivors, dead_cells = advance_generation(cells, config, rng)

    assert len(new_population) == len(cells)
    survivor_ids = {cell.cell_id for cell in survivors}
    replaced_ids = {cell.cell_id for cell in dead_cells}
    offspring = [cell for cell in new_population if cell.cell_id in replaced_ids]

    assert offspring
    for child in offspring:
        assert child.parent_cell_id in survivor_ids
        assert child.generation_index == 1
        assert config.f_min_min <= child.genes.f_min <= config.f_min_max
        assert config.mu_min <= child.genes.mu <= config.mu_max
        assert config.tau_min <= child.genes.tau <= config.tau_max
        assert config.beta_min <= child.genes.beta <= config.beta_max
