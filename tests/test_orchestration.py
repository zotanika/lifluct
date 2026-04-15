from pathlib import Path

from lifluct.core.cell import CellGenes
from lifluct.orchestration.manifest import ExperimentFamilyConfig, RegimeSpec, build_run_manifest
from lifluct.orchestration.scheduler import run_manifest_entries
from lifluct.reporting.experiment_registry import load_registry_rows
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
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def test_regime_family_integrity_keeps_shared_regime_variables(tmp_path) -> None:
    base_config = _config()
    family = ExperimentFamilyConfig(
        family_name="family_demo",
        description="demo",
        comparison_family="no_lysis",
        models=("dynamic_fee_single", "best_fixed_single_cell", "lifluct_multi_cell_no_lysis"),
        seed_start=1,
        seed_count=2,
        retention_mode="summary_only",
        best_fixed_genes=CellGenes(0.003, 0.2, 0.002, 0.1),
        regimes=(RegimeSpec(regime_id="demo_regime", config=base_config),),
    )
    manifest = build_run_manifest(family, output_root=tmp_path)

    for seed in [1, 2]:
        family_rows = [row for row in manifest if row.seed == seed]
        expected_regime = RegimeConfig.from_run_config(_config(seed=seed, lysis_mode="off"))
        actual_regimes = {RegimeConfig.from_run_config(RunConfig.from_mapping(row.config)) for row in family_rows}
        assert actual_regimes == {expected_regime}


def test_resume_skips_completed_runs_and_does_not_duplicate_registry(tmp_path) -> None:
    family = ExperimentFamilyConfig(
        family_name="family_resume",
        description="resume test",
        comparison_family="no_lysis",
        models=("dynamic_fee_single",),
        seed_start=1,
        seed_count=1,
        retention_mode="summary_only",
        regimes=(RegimeSpec(regime_id="demo_regime", config=_config(baseline_type="dynamic_fee_single", use_turgor=False, beta=0.0)),),
    )
    manifest = build_run_manifest(family, output_root=tmp_path)
    stats_first = run_manifest_entries(manifest, family_dir=tmp_path, max_workers=1, resume=True)
    stats_second = run_manifest_entries(manifest, family_dir=tmp_path, max_workers=1, resume=True)

    registry_rows = load_registry_rows(tmp_path / "registry.csv")
    assert stats_first["completed"] >= 1
    assert stats_second["skipped"] >= 1
    assert len(registry_rows) == 1
