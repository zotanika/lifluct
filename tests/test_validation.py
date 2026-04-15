from lifluct.reporting.validation import validate_result
from lifluct.types import ClusterState, RunConfig, RunSummary, SimulationResult


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
        "fee_max_global": 0.5,
        "lysis_mode": "off",
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def test_validation_flags_no_trade_run() -> None:
    config = _config()
    result = SimulationResult(
        config=config,
        final_state=ClusterState(1000.0, 100000.0),
        trades=[],
        step_metrics=[],
        summary=RunSummary(
            final_lp_value_b=200000.0,
            final_hodl_value_b=200000.0,
            lp_minus_hodl_b=0.0,
            total_lp_revenue_b=0.0,
            total_protocol_revenue_b=0.0,
            total_lp_fee_b=0.0,
            total_protocol_fee_b=0.0,
            total_attributed_loss_b=0.0,
            total_trader_cost_b=0.0,
            total_arbitrage_profit_b=0.0,
            num_trades=0,
            num_noise_trades=0,
            num_arbitrage_trades=0,
        ),
    )

    warnings, failure_modes = validate_result(result)

    assert any(warning.code == "no_trades" for warning in warnings)
    assert any(mode.mode == "dead_volume_equilibrium" for mode in failure_modes)
