from lifluct.core.attribution_modes import (
    evaluate_attribution_modes,
    reference_price_for_trade,
    ranking_stability,
    recompute_cell_attributed_loss,
)
from lifluct.types import CellSnapshot, RunConfig, StepMetric, TradeRecord


def _config(**updates: object) -> RunConfig:
    raw = {
        "seed": 1,
        "num_steps": 4,
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
        "attribution_lag_steps": 1,
        "attribution_twap_window": 2,
        "delayed_reference_steps": 1,
        "research_future_horizon": 2,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def _step_metrics() -> list[StepMetric]:
    return [
        StepMetric(0, 100.0, 100.0, 100.0, 1000.0, 100000.0, 200000.0, 200000.0, 200000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0),
        StepMetric(1, 102.0, 101.0, 100.5, 1000.0, 100000.0, 202000.0, 202000.0, 202000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1),
        StepMetric(2, 104.0, 103.0, 101.0, 1000.0, 100000.0, 204000.0, 204000.0, 204000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2),
        StepMetric(3, 110.0, 107.0, 102.0, 1000.0, 100000.0, 210000.0, 210000.0, 210000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3),
    ]


def _trade() -> TradeRecord:
    return TradeRecord(
        trade_id=1,
        step=2,
        actor_type="arbitrage",
        direction="b_to_a",
        amount_in=1000.0,
        amount_out=9.5,
        notional_b=1000.0,
        exec_price=105.0,
        oracle_price=103.0,
        pool_price_before=101.0,
        pool_price_after=102.0,
        fee_rate=0.01,
        lp_fee_amount_b=8.0,
        protocol_fee_amount_b=2.0,
        attributed_loss_b=0.0,
        trader_cost_b=10.0,
        cell_id=0,
    )


def test_twap_reference_differs_from_spot_when_window_is_nontrivial() -> None:
    config = _config()
    trade = _trade()
    spot = reference_price_for_trade(trade=trade, step_metrics=_step_metrics(), config=config, mode="observed_spot")
    twap = reference_price_for_trade(trade=trade, step_metrics=_step_metrics(), config=config, mode="twap")

    assert spot == 103.0
    assert twap != spot


def test_lagged_observed_uses_delayed_oracle_value() -> None:
    config = _config(attribution_lag_steps=1)
    lagged = reference_price_for_trade(trade=_trade(), step_metrics=_step_metrics(), config=config, mode="lagged_observed")

    assert lagged == 101.0


def test_research_ground_truth_proxy_is_separate_from_spot_reference() -> None:
    config = _config(research_future_horizon=1)
    losses_spot = recompute_cell_attributed_loss(
        trades=[_trade()],
        step_metrics=_step_metrics(),
        config=config,
        mode="observed_spot",
    )
    losses_truth = recompute_cell_attributed_loss(
        trades=[_trade()],
        step_metrics=_step_metrics(),
        config=config,
        mode="research_ground_truth_proxy",
    )

    assert losses_truth[0] != losses_spot[0]


def test_ranking_stability_reports_top_and_bottom_overlap_metrics() -> None:
    config = _config()
    snapshots = [
        CellSnapshot(0, 0, True, False, 0, None, 0.003, 0.1, 0.002, 0.1, 1000.0, 10.0, 0.0, 9.0, 2.0, 10.0, 1.0),
        CellSnapshot(0, 1, True, False, 0, None, 0.004, 0.2, 0.003, 0.2, 1000.0, 8.0, 0.0, 7.0, 5.0, 9.0, 0.5),
    ]
    results = evaluate_attribution_modes(
        config=config,
        trades=[_trade()],
        step_metrics=_step_metrics(),
        cell_snapshots=snapshots,
    )

    rows = ranking_stability(results)

    assert rows
    assert "fitness_top_1_overlap" in rows[0]
    assert "fitness_bottom_1_overlap" in rows[0]
