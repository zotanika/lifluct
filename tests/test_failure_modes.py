from lifluct.core.failure_modes import detect_failure_modes
from lifluct.types import CellSnapshot, EpochSummary, RunConfig, RunSummary


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
        "num_cells": 8,
        "fee_max_global": 0.5,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def _summary(**updates: object) -> RunSummary:
    raw = {
        "final_lp_value_b": 190000.0,
        "final_hodl_value_b": 200000.0,
        "lp_minus_hodl_b": -10000.0,
        "total_lp_revenue_b": 50.0,
        "total_protocol_revenue_b": 0.0,
        "total_lp_fee_b": 50.0,
        "total_protocol_fee_b": 0.0,
        "total_attributed_loss_b": 100.0,
        "total_trader_cost_b": 120.0,
        "total_arbitrage_profit_b": 40.0,
        "num_trades": 0,
        "num_noise_trades": 0,
        "num_arbitrage_trades": 0,
    }
    raw.update(updates)
    return RunSummary(**raw)


def test_dead_volume_failure_mode_triggers_on_obvious_dead_run() -> None:
    failures = detect_failure_modes(
        config=_config(),
        summary=_summary(),
        trades=[],
        step_metrics=[],
        epoch_summaries=[
            EpochSummary(0, 4, 0, 0, 0.0, 0.0, 10.0, 0.0, 5.0, 5.0, 100.0, 0.40, [], "[]")
        ],
        cell_snapshots=[],
    )

    dead_volume = next(mode for mode in failures if mode.mode == "dead_volume_equilibrium")
    assert dead_volume.severity in {"warning", "critical"}
    assert dead_volume.is_heuristic is True
    assert dead_volume.trigger_heuristic


def test_lysis_cascade_failure_mode_triggers_when_many_cells_lyse() -> None:
    failures = detect_failure_modes(
        config=_config(num_cells=8),
        summary=_summary(num_trades=10),
        trades=[],
        step_metrics=[],
        epoch_summaries=[
            EpochSummary(0, 8, 5, 0, 0.0, 0.0, 100.0, 0.0, 50.0, 60.0, 5000.0, 0.02, [], "[]")
        ],
        cell_snapshots=[
            CellSnapshot(0, 0, True, False, 0, None, 0.003, 0.1, 0.002, 0.1, 100.0, 5.0, 0.0, 6.0, 7.0, 5.0, 0.0)
        ],
    )

    lysis_cascade = next(mode for mode in failures if mode.mode == "lysis_cascade")
    assert lysis_cascade.severity == "critical"
    assert lysis_cascade.is_heuristic is True
