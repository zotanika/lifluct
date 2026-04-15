import json
import pytest
from run_index import RunIndex

@pytest.fixture
def index(tmp_path):
    return RunIndex(db_path=tmp_path / "test.db")

def test_register_and_list(index, tmp_path):
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()
    index.register(run_id="run_001", run_dir=str(run_dir), label="smoke test",
                   config_hash="abc123", config_summary={"baseline_type": "dynamic_fee_single", "seed": 42},
                   summary_metrics={"lp_minus_hodl_b": 100.0})
    runs = index.list_runs()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run_001"
    assert runs[0]["label"] == "smoke test"

def test_get_run(index, tmp_path):
    run_dir = tmp_path / "run_002"
    run_dir.mkdir()
    index.register(run_id="run_002", run_dir=str(run_dir), label="test", config_hash="def456")
    run = index.get_run("run_002")
    assert run is not None
    assert run["run_id"] == "run_002"
    assert index.get_run("nonexistent") is None

def test_list_with_filter(index, tmp_path):
    for i, label in enumerate(["dynamic smoke", "static smoke", "dynamic stress"]):
        d = tmp_path / f"run_{i}"
        d.mkdir()
        index.register(run_id=f"run_{i}", run_dir=str(d), label=label, config_hash=f"hash_{i}")
    dynamic_runs = index.list_runs(filter_label="dynamic")
    assert len(dynamic_runs) == 2
