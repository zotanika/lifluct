"""Experiment recommendation engine for LIFLUCT workflows."""
from __future__ import annotations

from typing import Any


def suggest_next(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze completed runs and recommend what to try next.

    Each run dict is expected to have optional keys:
        - summary_metrics: dict with at least lp_minus_hodl_b
        - failure_modes: list[dict] with mode/severity fields
        - config_summary: dict with oracle_mode, baseline_type, etc.
    """
    n = len(runs)

    # --- No runs: suggest smoke test ---
    if n == 0:
        return {
            "recommendation": "Run the smoke_dynamic preset to establish a baseline.",
            "rationale": (
                "No experiments have been run yet. A single smoke test with perfect "
                "oracle and low volatility confirms that the framework is working and "
                "gives you a baseline LP return to compare against."
            ),
            "estimated_runs": 1,
            "estimated_local_time_minutes": 1,
            "complexity": "single_run",
        }

    # --- Single run ---
    if n == 1:
        run = runs[0]
        failures = run.get("failure_modes", [])
        config = run.get("config_summary", {})
        oracle_mode = config.get("oracle_mode", "")
        baseline_type = config.get("baseline_type", "")

        # 1 run with failures
        if failures:
            severe = [f for f in failures if f.get("severity") in ("high", "critical")]
            return {
                "recommendation": (
                    "Investigate failure modes before expanding. Run 3-5 targeted "
                    "variants adjusting the parameters flagged in the failure evidence."
                ),
                "rationale": (
                    f"Your first run produced {len(failures)} failure mode(s) "
                    f"({len(severe)} high/critical). Expanding to more runs before "
                    f"understanding the root cause wastes compute. Adjust the flagged "
                    f"parameters (e.g., f_min, mu, oracle_lag_steps) one at a time."
                ),
                "estimated_runs": 4,
                "estimated_local_time_minutes": 5,
                "complexity": "single_run",
            }

        # 1 run with perfect oracle -> test lagged
        if oracle_mode == "perfect":
            return {
                "recommendation": (
                    "Test with a lagged oracle (oracle_lag_steps=3) to see if the "
                    "fee policy holds under realistic conditions."
                ),
                "rationale": (
                    "Your first run used a perfect oracle, which is the best case. "
                    "Real oracles have latency. Testing with lag reveals whether the "
                    "dynamic fee responds fast enough to protect LPs from toxic flow "
                    "during the lag window."
                ),
                "estimated_runs": 3,
                "estimated_local_time_minutes": 4,
                "complexity": "single_run",
            }

        # 1 run without comparison -> suggest static baseline
        has_comparison = any(
            r.get("config_summary", {}).get("baseline_type") == "static_cpmm"
            for r in runs
        )
        if not has_comparison:
            return {
                "recommendation": (
                    "Run the smoke_static preset to compare the dynamic fee policy "
                    "against a static CPMM baseline."
                ),
                "rationale": (
                    "You have one dynamic-fee run but no static baseline. Without a "
                    "comparison, you cannot tell if the dynamic fee's complexity is "
                    "justified. A static CPMM with the same price path provides a "
                    "clean A/B test."
                ),
                "estimated_runs": 1,
                "estimated_local_time_minutes": 1,
                "complexity": "single_run",
            }

    # --- 2-9 runs ---
    if 2 <= n <= 9:
        metrics = [
            r.get("summary_metrics", {}).get("lp_minus_hodl_b")
            for r in runs
            if r.get("summary_metrics", {}).get("lp_minus_hodl_b") is not None
        ]

        all_positive = all(m >= 0 for m in metrics) if metrics else False
        has_failures = any(r.get("failure_modes") for r in runs)

        if all_positive and not has_failures:
            return {
                "recommendation": (
                    "Run a best-fixed fee search to benchmark the dynamic policy "
                    "against the optimal static fee."
                ),
                "rationale": (
                    f"All {len(metrics)} runs with metrics show non-negative LP returns "
                    f"and no failure modes. The next step is to check whether a simple "
                    f"static fee could achieve the same result. A best-fixed search "
                    f"sweeps 8 fee levels on the same price path."
                ),
                "estimated_runs": 8,
                "estimated_local_time_minutes": 15,
                "complexity": "sweep",
            }
        else:
            return {
                "recommendation": (
                    "Run a 4-regime stress battery covering low-vol, high-vol, "
                    "lagged oracle, and sabotage scenarios."
                ),
                "rationale": (
                    f"Results are mixed across {n} runs (some negative LP returns or "
                    f"failure modes present). A structured 4-regime battery isolates "
                    f"which market conditions cause problems and which are robust."
                ),
                "estimated_runs": 4,
                "estimated_local_time_minutes": 8,
                "complexity": "sweep",
            }

    # --- 10+ runs: scaling ceiling ---
    return {
        "recommendation": (
            "Run a full regime family sweep (256 configurations) to map the "
            "entire parameter landscape."
        ),
        "rationale": (
            f"With {n} runs completed, you have enough signal to justify a "
            f"comprehensive sweep. A full regime family tests 256 combinations of "
            f"sigma, oracle_lag, toxic_mode, and fee parameters. This is the "
            f"scaling ceiling for single-machine evaluation and produces a complete "
            f"robustness map."
        ),
        "estimated_runs": 256,
        "estimated_local_time_minutes": 360,
        "complexity": "regime_family",
    }
