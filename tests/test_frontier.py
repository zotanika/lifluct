from lifluct.reporting.frontier import compute_lp_vs_trader_frontier, generate_frontier_outputs


def test_frontier_rows_compute_relative_lp_and_trader_metrics() -> None:
    rows = [
        {
            "label": "dynamic",
            "model_type": "dynamic_fee_single",
            "seed": 1,
            "sigma": 0.02,
            "oracle_lag_steps": 0,
            "toxic_mode": "cheapest_active",
            "fitness_mode": "basic_normalized",
            "lysis_mode": "off",
            "lp_minus_hodl_b": 10.0,
            "total_trader_cost_b": 5.0,
        },
        {
            "label": "lifluct",
            "model_type": "lifluct_multi_cell",
            "seed": 1,
            "sigma": 0.02,
            "oracle_lag_steps": 0,
            "toxic_mode": "cheapest_active",
            "fitness_mode": "basic_normalized",
            "lysis_mode": "off",
            "lp_minus_hodl_b": 15.0,
            "total_trader_cost_b": 7.0,
        },
    ]

    frontier_rows = compute_lp_vs_trader_frontier(rows)

    assert frontier_rows
    assert frontier_rows[-1]["lp_improvement_vs_baseline_b"] == 5.0
    assert frontier_rows[-1]["trader_cost_increase_vs_baseline_b"] == 2.0


def test_frontier_outputs_write_table_and_plots(tmp_path) -> None:
    rows = [
        {
            "label": "dynamic",
            "model_type": "dynamic_fee_single",
            "baseline_type": "dynamic_fee_single",
            "seed": 1,
            "sigma": 0.01,
            "oracle_lag_steps": 0,
            "toxic_mode": "cheapest_active",
            "fitness_mode": "basic_normalized",
            "lysis_mode": "off",
            "omega": 1.0,
            "kappa": 3.0,
            "lp_minus_hodl_b": 10.0,
            "total_trader_cost_b": 5.0,
            "total_attributed_loss_b": 3.0,
            "lysis_count": 0,
        },
        {
            "label": "lifluct",
            "model_type": "lifluct_multi_cell",
            "baseline_type": "lifluct_multi_cell",
            "seed": 1,
            "sigma": 0.02,
            "oracle_lag_steps": 1,
            "toxic_mode": "cheapest_active",
            "fitness_mode": "basic_normalized",
            "lysis_mode": "off",
            "omega": 1.5,
            "kappa": 3.0,
            "lp_minus_hodl_b": 12.0,
            "total_trader_cost_b": 6.0,
            "total_attributed_loss_b": 4.0,
            "lysis_count": 1,
        },
        {
            "label": "best_fixed",
            "model_type": "best_fixed_single_cell",
            "baseline_type": "best_fixed_single_cell",
            "seed": 1,
            "sigma": 0.02,
            "oracle_lag_steps": 1,
            "toxic_mode": "cheapest_active",
            "fitness_mode": "basic_normalized",
            "lysis_mode": "off",
            "omega": 1.5,
            "kappa": 3.0,
            "lp_minus_hodl_b": 11.0,
            "total_trader_cost_b": 5.5,
            "total_attributed_loss_b": 3.5,
            "lysis_count": 0,
        },
    ]

    outputs = generate_frontier_outputs(rows, output_dir=tmp_path)

    assert outputs["frontier_table"]
    assert (tmp_path / "frontier_rows.csv").exists()
    assert outputs["plot_paths"]
