import sys
from dataclasses import replace

from lifluct.cli import export_report_bundle
from lifluct.cli.run_simulation import execute_and_write_run
from lifluct.reporting.compare import generate_comparison_outputs, load_runs
from lifluct.types import RunConfig


def _config(**updates: object) -> RunConfig:
    raw = {
        "seed": 1,
        "num_steps": 20,
        "initial_reserve_a": 1000.0,
        "initial_reserve_b": 100000.0,
        "initial_price": 100.0,
        "sigma": 0.02,
        "q_trade": 0.3,
        "max_trade_fraction_of_tvl": 0.02,
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


def test_comparison_outputs_include_rows_and_report_tables(tmp_path) -> None:
    first_dir = tmp_path / "run_one"
    second_dir = tmp_path / "run_two"
    execute_and_write_run(_config(seed=1), first_dir, metadata={"label": "dynamic"})
    execute_and_write_run(_config(seed=2), second_dir, metadata={"label": "dynamic"})

    payloads = load_runs([first_dir, second_dir])
    outputs = generate_comparison_outputs(payloads, output_dir=tmp_path / "comparison", group_by=["label"])

    assert outputs["rows"]
    assert outputs["aggregated"]
    assert "lp_minus_hodl_b" in outputs["comparison_table"]
    assert outputs["regime_definition_block"]
    assert "mode" in outputs["attribution_robustness_table"] or outputs["attribution_robustness_table"] == "_No rows._"


def test_export_report_bundle_copies_selected_directories(tmp_path, monkeypatch) -> None:
    run_dir = tmp_path / "run_one"
    comparison_dir = tmp_path / "comparison_one"
    experiment_dir = tmp_path / "experiment_one"
    bundle_dir = tmp_path / "bundle"

    for directory in [run_dir, comparison_dir, experiment_dir]:
        directory.mkdir()
        (directory / "marker.txt").write_text("ok\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "export_report_bundle",
            "--run-dir",
            str(run_dir),
            "--comparison-dir",
            str(comparison_dir),
            "--experiment-dir",
            str(experiment_dir),
            "--output-dir",
            str(bundle_dir),
        ],
    )
    export_report_bundle.main()

    assert (bundle_dir / "runs" / run_dir.name / "marker.txt").exists()
    assert (bundle_dir / "comparisons" / comparison_dir.name / "marker.txt").exists()
    assert (bundle_dir / "experiments" / experiment_dir.name / "marker.txt").exists()
    assert (bundle_dir / "index.md").exists()
