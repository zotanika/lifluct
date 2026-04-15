from lifluct.reporting.aggregate_stats import aggregate_result_rows
from lifluct.reporting.bootstrap import bootstrap_confidence_interval


def test_aggregate_stats_compute_mean_and_median() -> None:
    rows = [
        {"model_type": "dynamic_fee_single", "lp_minus_hodl_b": 1.0, "total_lp_revenue_b": 2.0, "total_attributed_loss_b": 0.5, "total_trader_cost_b": 0.2, "total_arbitrage_profit_b": 0.1, "lysis_count": 0, "active_cell_count": 1, "top_cell_concentration_final": 1.0, "failure_modes_count": 0},
        {"model_type": "dynamic_fee_single", "lp_minus_hodl_b": 3.0, "total_lp_revenue_b": 4.0, "total_attributed_loss_b": 1.5, "total_trader_cost_b": 0.4, "total_arbitrage_profit_b": 0.2, "lysis_count": 0, "active_cell_count": 1, "top_cell_concentration_final": 1.0, "failure_modes_count": 1},
    ]

    aggregated = aggregate_result_rows(rows, group_by=["model_type"])

    assert aggregated[0]["lp_minus_hodl_b_mean"] == 2.0
    assert aggregated[0]["lp_minus_hodl_b_median"] == 2.0
    assert aggregated[0]["downside_frequency_lp_minus_hodl_b"] == 0.0


def test_bootstrap_confidence_interval_returns_expected_structure() -> None:
    interval = bootstrap_confidence_interval([1.0, 2.0, 3.0], metric="median", num_bootstrap=50, seed=11)

    assert interval["metric"] == "median"
    assert interval["num_samples"] == 3
    assert float(interval["lower"]) <= float(interval["upper"])
