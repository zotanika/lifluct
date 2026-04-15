"""Named experiment presets for zero-knowledge entry."""
from __future__ import annotations
from copy import deepcopy
from typing import Any

_BASE = {
    "seed": 42,
    "initial_reserve_a": 1000.0,
    "initial_reserve_b": 100000.0,
    "initial_price": 100.0,
    "q_trade": 0.35,
    "max_trade_fraction_of_tvl": 0.02,
    "arbitrage_threshold": 0.001,
    "tvl_target": 200000.0,
    "dt": 1.0,
    "oracle_observation_noise": 0.01,
    "num_cells": 1,
    "epoch_length": 100,
    "use_turgor": False,
    "enable_evolution": False,
    "lysis_mode": "off",
    "attribution_mode": "observed_spot",
    "user_routing_mode": "weighted_random",
    "s_base": 1.0,
    "beta": 0.0,
}

PRESETS: list[dict[str, Any]] = [
    {
        "name": "smoke_dynamic",
        "description": "Quick dynamic fee test. ~1 min. Perfect oracle, low volatility.",
        "category": "smoke_test",
        "estimated_seconds": 60,
        "config": {**_BASE, "num_steps": 400, "sigma": 0.02, "baseline_type": "dynamic_fee_single",
                   "use_dynamic_fee": True, "oracle_mode": "perfect", "oracle_lag_steps": 0,
                   "f_min": 0.003, "mu": 0.15, "tau": 0.002, "toxic_mode": "cheapest_active"},
    },
    {
        "name": "smoke_static",
        "description": "Quick static CPMM baseline. ~1 min. The simplest AMM.",
        "category": "smoke_test",
        "estimated_seconds": 60,
        "config": {**_BASE, "num_steps": 400, "sigma": 0.02, "baseline_type": "static_cpmm",
                   "use_dynamic_fee": False, "oracle_mode": "perfect", "oracle_lag_steps": 0,
                   "f_min": 0.003, "mu": 0.0, "tau": 0.0, "toxic_mode": "cheapest_active"},
    },
    {
        "name": "stress_oracle_lag",
        "description": "Dynamic fee under lagged oracle (3 steps). Tests oracle fragility.",
        "category": "stress_test",
        "estimated_seconds": 120,
        "config": {**_BASE, "num_steps": 1000, "sigma": 0.03, "baseline_type": "dynamic_fee_single",
                   "use_dynamic_fee": True, "oracle_mode": "lagged", "oracle_lag_steps": 3,
                   "f_min": 0.003, "mu": 0.15, "tau": 0.002, "toxic_mode": "fee_aware_max_extraction"},
    },
    {
        "name": "stress_high_vol",
        "description": "Dynamic fee under high volatility (sigma=0.08). Tests fee responsiveness.",
        "category": "stress_test",
        "estimated_seconds": 120,
        "config": {**_BASE, "num_steps": 1000, "sigma": 0.08, "baseline_type": "dynamic_fee_single",
                   "use_dynamic_fee": True, "oracle_mode": "perfect", "oracle_lag_steps": 0,
                   "f_min": 0.003, "mu": 0.15, "tau": 0.002, "toxic_mode": "fee_aware_max_extraction"},
    },
    {
        "name": "stress_sabotage",
        "description": "Dynamic fee under sabotage adversary. Maximum adversarial pressure.",
        "category": "stress_test",
        "estimated_seconds": 120,
        "config": {**_BASE, "num_steps": 1000, "sigma": 0.03, "baseline_type": "dynamic_fee_single",
                   "use_dynamic_fee": True, "oracle_mode": "lagged", "oracle_lag_steps": 2,
                   "f_min": 0.003, "mu": 0.15, "tau": 0.002, "toxic_mode": "sabotage"},
    },
]


def list_presets(*, category: str | None = None) -> list[dict[str, Any]]:
    result = []
    for p in PRESETS:
        if category and p["category"] != category:
            continue
        result.append({
            "name": p["name"],
            "description": p["description"],
            "category": p["category"],
            "estimated_seconds": p.get("estimated_seconds", 60),
        })
    return result


def get_preset(name: str, *, overrides: dict[str, Any] | None = None) -> dict[str, Any] | None:
    for p in PRESETS:
        if p["name"] == name:
            result = deepcopy(p)
            if overrides and "config" in result:
                result["config"].update(overrides)
            return result
    return None
