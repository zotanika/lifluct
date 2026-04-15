from lifluct.core.cell import CellGenes, CellState
from lifluct.reporting.experiment_registry import compute_config_hash, make_registry_record
from lifluct.types import RunConfig, RunSummary


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
        "num_cells": 4,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def test_config_hash_is_stable() -> None:
    config = _config()
    assert compute_config_hash(config) == compute_config_hash(config.to_dict())


def test_registry_record_captures_key_summary_fields() -> None:
    config = _config()
    summary = RunSummary(
        final_lp_value_b=210000.0,
        final_hodl_value_b=200000.0,
        lp_minus_hodl_b=10000.0,
        total_lp_revenue_b=500.0,
        total_protocol_revenue_b=50.0,
        total_lp_fee_b=500.0,
        total_protocol_fee_b=50.0,
        total_attributed_loss_b=100.0,
        total_trader_cost_b=120.0,
        total_arbitrage_profit_b=30.0,
        num_trades=10,
        num_noise_trades=5,
        num_arbitrage_trades=5,
    )
    cell = CellState(
        cell_id=0,
        active=True,
        lysis_triggered=False,
        generation_index=0,
        parent_cell_id=None,
        genes=CellGenes(0.003, 0.1, 0.002, 0.1),
    )
    snapshot = cell.snapshot(epoch_index=0, fitness=1.0)

    record = make_registry_record(
        experiment_id="exp",
        run_id="run_0000",
        run_dir="runs/exp/run_0000",
        label="lifluct",
        config=config,
        summary=summary,
        cell_snapshots=[snapshot],
        warnings_count=1,
        failure_modes_count=2,
    )

    assert record.experiment_id == "exp"
    assert record.label == "lifluct"
    assert record.lp_minus_hodl_b == 10000.0
    assert record.model_type == "lifluct_multi_cell"
    assert record.model_family == "no_lysis"
    assert record.regime_id.startswith("regime_")
    assert record.attribution_mode == "observed_spot"
    assert record.warnings_count == 1
    assert record.failure_modes_count == 2
