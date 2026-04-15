from lifluct.cli.run_simulation import execute_and_write_run
from lifluct.types import RunConfig


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
        "baseline_type": "dynamic_fee_single",
        "f_min": 0.003,
        "mu": 0.15,
        "tau": 0.002,
        "s_base": 1.0,
        "beta": 0.0,
        "tvl_target": 200000.0,
        "oracle_mode": "perfect",
        "oracle_lag_steps": 0,
        "use_dynamic_fee": True,
        "use_turgor": False,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def test_full_trace_retention_stores_trade_logs(tmp_path) -> None:
    run_dir = tmp_path / "full_trace"
    execute_and_write_run(_config(), run_dir, retention_mode="full_trace")

    assert (run_dir / "trades.csv").exists()
    assert (run_dir / "step_metrics.csv").exists()
    assert (run_dir / "summary.json").exists()


def test_epoch_only_retention_omits_trade_logs(tmp_path) -> None:
    run_dir = tmp_path / "epoch_only"
    execute_and_write_run(
        _config(baseline_type="lifluct_multi_cell", num_cells=4, use_turgor=True, beta=0.2, enable_evolution=True),
        run_dir,
        retention_mode="epoch_only",
    )

    assert not (run_dir / "trades.csv").exists()
    assert not (run_dir / "step_metrics.csv").exists()
    assert (run_dir / "epoch_summaries.csv").exists()
    assert (run_dir / "cell_snapshots.csv").exists()


def test_summary_only_retention_stores_only_summary_artifacts(tmp_path) -> None:
    run_dir = tmp_path / "summary_only"
    execute_and_write_run(
        _config(baseline_type="lifluct_multi_cell", num_cells=4, use_turgor=True, beta=0.2, enable_evolution=True),
        run_dir,
        retention_mode="summary_only",
    )

    assert (run_dir / "summary.json").exists()
    assert (run_dir / "diagnostics.json").exists()
    assert not (run_dir / "trades.csv").exists()
    assert not (run_dir / "epoch_summaries.csv").exists()
    assert not (run_dir / "cell_snapshots.csv").exists()
