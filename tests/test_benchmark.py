from lifluct.core.benchmark import (
    build_model_suite_for_regime,
    family_model_types,
    regime_for_family,
    search_best_fixed_single_cell,
)
from lifluct.core.cell import CellGenes
from lifluct.types import RegimeConfig, RunConfig


def _config(**updates: object) -> RunConfig:
    raw = {
        "seed": 1,
        "num_steps": 20,
        "epoch_length": 10,
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
        "num_cells": 4,
        "enable_evolution": True,
        "f_min_min": 0.0005,
        "f_min_max": 0.01,
        "mu_min": 0.0,
        "mu_max": 2.0,
        "tau_min": 0.0001,
        "tau_max": 0.02,
        "beta_min": 0.0,
        "beta_max": 1.0,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def test_best_fixed_search_returns_gene_vector_within_bounds() -> None:
    result = search_best_fixed_single_cell(
        train_configs=[_config(seed=1)],
        search_budget=4,
        objective_mode="lp_minus_hodl",
        search_seed=9,
    )

    assert 0.0005 <= result.best_genes.f_min <= 0.01
    assert 0.0 <= result.best_genes.mu <= 2.0
    assert 0.0001 <= result.best_genes.tau <= 0.02
    assert 0.0 <= result.best_genes.beta <= 1.0
    assert result.search_budget == 4
    assert result.search_profile == "serious"


def test_best_fixed_search_keeps_train_and_test_evaluations_separate() -> None:
    result = search_best_fixed_single_cell(
        train_configs=[_config(seed=1, sigma=0.02)],
        test_configs=[_config(seed=2, sigma=0.05)],
        search_budget=4,
        objective_mode="lp_minus_hodl",
        search_seed=9,
    )

    assert result.train_rows
    assert result.test_rows
    assert all(row["dataset"] == "train" for row in result.train_rows)
    assert all(row["dataset"] == "test" for row in result.test_rows)


def test_best_fixed_search_applies_family_level_lysis_override() -> None:
    result = search_best_fixed_single_cell(
        train_configs=[_config(seed=1, lysis_mode="off")],
        test_configs=[_config(seed=2, lysis_mode="hard")],
        search_budget=2,
        objective_mode="lp_minus_hodl",
        search_seed=9,
        family="no_lysis",
    )

    assert result.test_rows
    assert all(row["lysis_mode"] == "off" for row in result.test_rows)


def test_suite_fairness_keeps_same_regime_for_every_model() -> None:
    config = _config(seed=3, lysis_mode="off")
    regime = regime_for_family(RegimeConfig.from_run_config(config), "no_lysis")
    suite = build_model_suite_for_regime(
        template_config=config,
        regime=regime,
        family="no_lysis",
        best_fixed_genes=CellGenes(0.003, 0.2, 0.002, 0.1),
    )

    actual_regimes = {RegimeConfig.from_run_config(model_config) for model_config in suite.values()}
    assert actual_regimes == {regime}


def test_family_model_types_keep_lysis_and_no_lysis_separate() -> None:
    assert family_model_types("no_lysis") == [
        "static_cpmm",
        "dynamic_fee_single",
        "best_fixed_single_cell",
        "lifluct_multi_cell_no_lysis",
    ]
    assert family_model_types("lysis_enabled") == [
        "dynamic_fee_single_with_lysis",
        "best_fixed_single_cell_with_lysis",
        "lifluct_multi_cell_with_lysis",
    ]
