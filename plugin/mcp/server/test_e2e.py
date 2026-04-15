"""End-to-end integration test for LIFLUCT MCP server.

Exercises the full flow: presets -> run index -> knowledge -> advisor,
verifying that all modules integrate correctly without running actual
simulations.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure server modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from presets import get_preset, list_presets
from run_index import RunIndex
from advisor import suggest_next
from knowledge import explain_concept, list_concepts


def test_full_integration(tmp_path: Path) -> None:
    """Integration test: presets -> index -> advisor pipeline."""

    # 1. List and get preset
    presets = list_presets()
    assert len(presets) >= 3

    preset = get_preset("smoke_dynamic")
    assert preset is not None
    assert preset["config"]["baseline_type"] == "dynamic_fee_single"

    # 2. Register mock runs in index
    index = RunIndex(db_path=tmp_path / "test.db")

    index.register(
        run_id="run_dynamic_001",
        run_dir=str(tmp_path / "run1"),
        label="dynamic smoke",
        config_hash="abc",
        config_summary={"baseline_type": "dynamic_fee_single", "seed": 42},
        summary_metrics={
            "lp_minus_hodl_b": 6099.58,
            "total_attributed_loss_b": 9754.35,
            "total_lp_revenue_b": 5990.06,
        },
    )
    index.register(
        run_id="run_static_001",
        run_dir=str(tmp_path / "run2"),
        label="static smoke",
        config_hash="def",
        config_summary={"baseline_type": "static_cpmm", "seed": 42},
        summary_metrics={
            "lp_minus_hodl_b": 3000.0,
            "total_attributed_loss_b": 5000.0,
            "total_lp_revenue_b": 4000.0,
        },
    )

    # 3. List and filter
    all_runs = index.list_runs()
    assert len(all_runs) == 2

    dynamic_runs = index.list_runs(filter_label="dynamic")
    assert len(dynamic_runs) == 1

    # 4. Get specific run
    run = index.get_run("run_dynamic_001")
    assert run is not None
    assert run["summary_metrics"]["lp_minus_hodl_b"] == 6099.58

    # 5. Explain concept
    result = explain_concept("toxic_flow")
    assert result is not None
    assert result["ok"] is True
    assert "title" in result

    # 6. Get advisor recommendation
    runs_for_advisor = [
        {
            "summary_metrics": {"lp_minus_hodl_b": 6099.58},
            "failure_modes": [],
            "config_summary": {
                "baseline_type": "dynamic_fee_single",
                "oracle_mode": "perfect",
            },
        },
        {
            "summary_metrics": {"lp_minus_hodl_b": 3000.0},
            "failure_modes": [],
            "config_summary": {
                "baseline_type": "static_cpmm",
                "oracle_mode": "perfect",
            },
        },
    ]
    suggestion = suggest_next(runs_for_advisor)
    assert "recommendation" in suggestion
    assert "estimated_runs" in suggestion
    assert "estimated_local_time_minutes" in suggestion
    assert suggestion["complexity"] in ("single_run", "sweep", "regime_family")


def test_preset_config_validates(tmp_path: Path) -> None:
    """All preset configs contain the fields that configure_experiment produces."""
    required_fields = [
        "baseline_type",
        "sigma",
        "num_steps",
        "seed",
        "oracle_mode",
        "toxic_mode",
    ]
    for preset_info in list_presets():
        preset = get_preset(preset_info["name"])
        assert preset is not None, f"get_preset returned None for {preset_info['name']}"
        config = preset["config"]
        for field in required_fields:
            assert field in config, (
                f"Preset {preset_info['name']!r} missing required field {field!r}"
            )


def test_knowledge_covers_key_concepts() -> None:
    """All concepts referenced in presets/advisor have knowledge entries."""
    key_concepts = ["amm", "lp", "toxic_flow", "attribution", "oracle", "regime"]
    for concept in key_concepts:
        result = explain_concept(concept)
        assert result["ok"] is True, f"Missing knowledge entry for {concept!r}"
        assert len(result["detail"]) > 50, (
            f"Knowledge entry for {concept!r} is too short"
        )


def test_advisor_progression() -> None:
    """Advisor recommendations progress through complexity tiers."""
    # Tier 0: no runs
    s0 = suggest_next([])
    assert s0["complexity"] == "single_run"

    # Tier 1: single run, perfect oracle, no failures
    s1 = suggest_next([
        {
            "summary_metrics": {"lp_minus_hodl_b": 100.0},
            "failure_modes": [],
            "config_summary": {"oracle_mode": "perfect"},
        }
    ])
    assert s1["complexity"] == "single_run"
    assert s1["estimated_runs"] >= 1

    # Tier 2: multiple positive runs, no failures
    s2 = suggest_next([
        {
            "summary_metrics": {"lp_minus_hodl_b": float(i * 10)},
            "failure_modes": [],
            "config_summary": {},
        }
        for i in range(5)
    ])
    assert s2["complexity"] == "sweep"
    assert s2["estimated_runs"] >= 4

    # Tier 3: 10+ runs
    s3 = suggest_next([
        {
            "summary_metrics": {"lp_minus_hodl_b": float(i)},
            "failure_modes": [],
            "config_summary": {},
        }
        for i in range(12)
    ])
    assert s3["complexity"] == "regime_family"
    assert s3["estimated_runs"] >= 64


def test_index_compare_flow(tmp_path: Path) -> None:
    """Register runs and verify comparison data can be extracted."""
    index = RunIndex(db_path=tmp_path / "compare.db")

    # Register two runs with different metrics
    index.register(
        run_id="cmp_a",
        run_dir=str(tmp_path / "cmp_a"),
        label="dynamic fee",
        config_hash="aaa",
        config_summary={"baseline_type": "dynamic_fee_single"},
        summary_metrics={"lp_minus_hodl_b": 6099.58, "total_lp_revenue_b": 5990.06},
    )
    index.register(
        run_id="cmp_b",
        run_dir=str(tmp_path / "cmp_b"),
        label="static cpmm",
        config_hash="bbb",
        config_summary={"baseline_type": "static_cpmm"},
        summary_metrics={"lp_minus_hodl_b": 3000.0, "total_lp_revenue_b": 4000.0},
    )

    # Retrieve both and compare
    run_a = index.get_run("cmp_a")
    run_b = index.get_run("cmp_b")
    assert run_a is not None
    assert run_b is not None

    # Determine winner by lp_minus_hodl_b
    metrics = [
        (run_a["run_id"], run_a["summary_metrics"]["lp_minus_hodl_b"]),
        (run_b["run_id"], run_b["summary_metrics"]["lp_minus_hodl_b"]),
    ]
    winner = max(metrics, key=lambda x: x[1])
    assert winner[0] == "cmp_a"
    assert winner[1] == 6099.58


def test_suggest_after_compare(tmp_path: Path) -> None:
    """After registering and comparing runs, advisor gives actionable suggestion."""
    index = RunIndex(db_path=tmp_path / "suggest.db")

    index.register(
        run_id="s_dynamic",
        run_dir=str(tmp_path / "s_dynamic"),
        label="dynamic",
        config_hash="d1",
        config_summary={
            "baseline_type": "dynamic_fee_single",
            "oracle_mode": "perfect",
        },
        summary_metrics={"lp_minus_hodl_b": 6099.58},
    )
    index.register(
        run_id="s_static",
        run_dir=str(tmp_path / "s_static"),
        label="static",
        config_hash="s1",
        config_summary={
            "baseline_type": "static_cpmm",
            "oracle_mode": "perfect",
        },
        summary_metrics={"lp_minus_hodl_b": 3000.0},
    )

    # Build advisor input from index data
    run_data = []
    for rid in ["s_dynamic", "s_static"]:
        info = index.get_run(rid)
        assert info is not None
        run_data.append({
            "summary_metrics": info["summary_metrics"],
            "failure_modes": [],
            "config_summary": info["config_summary"],
        })

    suggestion = suggest_next(run_data)
    assert "recommendation" in suggestion
    assert suggestion["estimated_runs"] >= 1
    assert suggestion["complexity"] in ("single_run", "sweep", "regime_family")
