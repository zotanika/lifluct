import pytest
from presets import list_presets, get_preset

def test_list_presets_returns_all():
    result = list_presets()
    assert len(result) >= 3
    assert all("name" in p for p in result)
    assert all("description" in p for p in result)

def test_list_presets_filter_by_category():
    result = list_presets(category="stress_test")
    assert all(p["category"] == "stress_test" for p in result)
    assert len(result) >= 2

def test_get_preset_returns_config():
    preset = get_preset("smoke_dynamic")
    assert preset is not None
    assert preset["config"]["baseline_type"] == "dynamic_fee_single"
    assert preset["config"]["num_steps"] <= 500

def test_get_preset_unknown():
    assert get_preset("nonexistent") is None

def test_get_preset_with_overrides():
    preset = get_preset("smoke_dynamic", overrides={"seed": 99, "sigma": 0.05})
    assert preset["config"]["seed"] == 99
    assert preset["config"]["sigma"] == 0.05
