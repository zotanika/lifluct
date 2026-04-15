"""Tests for MCP tool registration, knowledge base, and advisor."""
import pytest

from server import create_server
from knowledge import explain_concept, list_concepts
from advisor import suggest_next


# -------------------------------------------------------------------
# Tool registration
# -------------------------------------------------------------------
EXPECTED_TOOLS = [
    "health",
    "list_presets",
    "run_preset",
    "explain_concept",
    "configure_experiment",
    "validate_config",
    "run_experiment",
    "read_results",
    "list_runs",
    "compare_runs",
    "read_attribution_robustness",
    "suggest_next_experiment",
]


@pytest.mark.anyio
async def test_all_expected_tools_registered():
    server = create_server()
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    for expected in EXPECTED_TOOLS:
        assert expected in tool_names, f"Missing tool: {expected}"


@pytest.mark.anyio
async def test_no_unexpected_tools():
    server = create_server()
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    # Every registered tool should be in our expected list
    for name in tool_names:
        assert name in EXPECTED_TOOLS, f"Unexpected tool: {name}"


# -------------------------------------------------------------------
# Knowledge base
# -------------------------------------------------------------------
def test_explain_concept_known():
    result = explain_concept("amm")
    assert result["ok"] is True
    assert result["concept"] == "amm"
    assert "title" in result
    assert "short" in result
    assert "detail" in result
    assert "relevance" in result


def test_explain_concept_normalisation():
    """Ensure lookup handles whitespace, dashes, and case."""
    result = explain_concept("  Toxic-Flow  ")
    assert result["ok"] is True
    assert result["concept"] == "toxic_flow"


def test_explain_concept_unknown():
    result = explain_concept("nonexistent_widget")
    assert result["ok"] is False
    assert "available_concepts" in result


def test_list_concepts_returns_all():
    concepts = list_concepts()
    assert len(concepts) == 8
    keys = {c["concept"] for c in concepts}
    assert "amm" in keys
    assert "oracle" in keys
    assert all("title" in c and "short" in c for c in concepts)


# -------------------------------------------------------------------
# Advisor
# -------------------------------------------------------------------
def test_suggest_next_no_runs():
    result = suggest_next([])
    assert result["complexity"] == "single_run"
    assert result["estimated_runs"] == 1
    assert "recommendation" in result
    assert "rationale" in result


def test_suggest_next_single_run_with_failures():
    runs = [
        {
            "summary_metrics": {"lp_minus_hodl_b": -50.0},
            "failure_modes": [{"mode": "fee_too_low", "severity": "high"}],
            "config_summary": {"oracle_mode": "perfect"},
        }
    ]
    result = suggest_next(runs)
    assert result["complexity"] == "single_run"
    assert result["estimated_runs"] == 4


def test_suggest_next_single_run_perfect_oracle():
    runs = [
        {
            "summary_metrics": {"lp_minus_hodl_b": 100.0},
            "failure_modes": [],
            "config_summary": {"oracle_mode": "perfect"},
        }
    ]
    result = suggest_next(runs)
    assert "lagged" in result["recommendation"].lower()


def test_suggest_next_single_run_no_comparison():
    runs = [
        {
            "summary_metrics": {"lp_minus_hodl_b": 100.0},
            "failure_modes": [],
            "config_summary": {"oracle_mode": "lagged", "baseline_type": "dynamic_fee_single"},
        }
    ]
    result = suggest_next(runs)
    assert "static" in result["recommendation"].lower()


def test_suggest_next_multiple_all_positive():
    runs = [
        {
            "summary_metrics": {"lp_minus_hodl_b": 50.0},
            "failure_modes": [],
            "config_summary": {},
        }
        for _ in range(5)
    ]
    result = suggest_next(runs)
    assert result["complexity"] == "sweep"
    assert result["estimated_runs"] == 8


def test_suggest_next_multiple_mixed():
    runs = [
        {
            "summary_metrics": {"lp_minus_hodl_b": 50.0},
            "failure_modes": [],
            "config_summary": {},
        },
        {
            "summary_metrics": {"lp_minus_hodl_b": -20.0},
            "failure_modes": [],
            "config_summary": {},
        },
        {
            "summary_metrics": {"lp_minus_hodl_b": 10.0},
            "failure_modes": [],
            "config_summary": {},
        },
    ]
    result = suggest_next(runs)
    assert result["complexity"] == "sweep"
    assert result["estimated_runs"] == 4


def test_suggest_next_ten_plus_runs():
    runs = [
        {
            "summary_metrics": {"lp_minus_hodl_b": float(i)},
            "failure_modes": [],
            "config_summary": {},
        }
        for i in range(12)
    ]
    result = suggest_next(runs)
    assert result["complexity"] == "regime_family"
    assert result["estimated_runs"] == 256
    assert result["estimated_local_time_minutes"] == 360


# -------------------------------------------------------------------
# Presets integration (verify they still work through server)
# -------------------------------------------------------------------
def test_presets_integration():
    from presets import list_presets, get_preset

    presets = list_presets()
    assert len(presets) >= 3
    smoke = get_preset("smoke_dynamic")
    assert smoke is not None
    assert smoke["config"]["baseline_type"] == "dynamic_fee_single"
