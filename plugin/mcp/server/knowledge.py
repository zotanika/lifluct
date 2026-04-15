"""Domain concept dictionary for LIFLUCT experiment interpretation."""
from __future__ import annotations

from typing import Any

_CONCEPTS: dict[str, dict[str, str]] = {
    "amm": {
        "title": "Automated Market Maker (AMM)",
        "short": "A smart contract that provides liquidity via a deterministic pricing function instead of an order book.",
        "detail": (
            "An AMM holds reserves of two assets and prices trades using a bonding curve "
            "(e.g., constant-product x*y=k). Liquidity providers deposit assets and earn fees "
            "from every trade. The AMM continuously offers prices, removing the need for "
            "counterparty matching. Key parameters include the fee schedule, reserve sizes, "
            "and the invariant function shape."
        ),
        "relevance": (
            "LIFLUCT simulates a single AMM pool to evaluate how different fee policies, "
            "oracle configurations, and adversarial trading strategies affect LP returns. "
            "Every experiment result is measured against this AMM's performance."
        ),
    },
    "lp": {
        "title": "Liquidity Provider (LP)",
        "short": "An agent who deposits assets into an AMM pool and earns trading fees in return.",
        "detail": (
            "LPs supply capital that enables trading. Their return depends on fees earned "
            "minus impermanent loss (divergence loss). In LIFLUCT, the primary metric is "
            "lp_minus_hodl_b: the LP portfolio value minus what they would have earned by "
            "simply holding the initial assets. Positive values mean the fee policy "
            "compensated for divergence loss."
        ),
        "relevance": (
            "The core question LIFLUCT answers is whether a fee policy makes LPs better off "
            "than holding. Summary metrics like lp_minus_hodl_b, total_lp_revenue_b, and "
            "total_attributed_loss_b directly measure LP welfare."
        ),
    },
    "toxic_flow": {
        "title": "Toxic Flow (Adverse Selection)",
        "short": "Trades executed by informed arbitrageurs that systematically extract value from LPs.",
        "detail": (
            "When an arbitrageur knows the true price has moved before the AMM updates, "
            "they trade at the stale price and pocket the difference. This flow is 'toxic' "
            "because it transfers value from LPs to arbitrageurs. The severity depends on "
            "oracle latency, volatility, and the fee level. Dynamic fees attempt to price "
            "this risk by raising fees when toxic flow is likely."
        ),
        "relevance": (
            "LIFLUCT models toxic flow via toxic_mode (cheapest_active, fee_aware_max_extraction, "
            "sabotage). The total_arbitrage_profit_b and total_attributed_loss_b metrics "
            "quantify how much value the adversary extracted. Failure modes flag when "
            "toxic flow overwhelms fee revenue."
        ),
    },
    "attribution": {
        "title": "Loss Attribution Mode",
        "short": "The method used to measure how much value each trade cost or earned for LPs.",
        "detail": (
            "Attribution answers: 'was this trade good or bad for LPs, and by how much?' "
            "Different reference prices (observed spot, TWAP, delayed) yield different "
            "answers. LIFLUCT supports several modes and can evaluate robustness by running "
            "all modes on the same simulation trace. If results change materially across "
            "modes, conclusions are fragile."
        ),
        "relevance": (
            "The attribution_mode config field selects the primary mode. The "
            "read_attribution_robustness tool loads the multi-mode comparison from "
            "attribution_mode_comparison.json and attribution_ranking_stability.json."
        ),
    },
    "best_fixed": {
        "title": "Best Fixed Fee (Benchmark)",
        "short": "The optimal constant fee that maximizes LP returns in hindsight for a given price path.",
        "detail": (
            "Best-fixed search replays the same price path with many static fee levels and "
            "picks the one with the highest lp_minus_hodl_b. It is the strongest benchmark "
            "for a dynamic fee policy: if the dynamic policy cannot beat the best fixed fee, "
            "its complexity is not justified. This is a computationally expensive search "
            "(typically 128-256 fee levels)."
        ),
        "relevance": (
            "The suggest_next_experiment advisor recommends a best-fixed search once initial "
            "smoke tests pass. Comparing dynamic policy results against best_fixed reveals "
            "whether adaptivity adds value."
        ),
    },
    "lysis": {
        "title": "Lysis (Cell Death)",
        "short": "The removal of underperforming fee-parameter cells in a multi-cell turgor AMM.",
        "detail": (
            "In turgor mode, the AMM runs multiple cells with different fee parameters. "
            "Lysis kills cells whose fitness falls below a threshold (controlled by kappa). "
            "Modes include 'off', 'hard' (immediate removal), and 'soft' (gradual penalty). "
            "Lysis prevents dead-weight cells from diluting the pool but can reduce diversity "
            "too aggressively."
        ),
        "relevance": (
            "The lysis_mode config field controls this. Summary metrics total_lysis_count "
            "and total_dead_cells show how many cells were removed. High lysis with good "
            "LP returns suggests effective evolutionary pressure."
        ),
    },
    "regime": {
        "title": "Volatility Regime",
        "short": "A distinct market environment characterized by its volatility level and toxic flow intensity.",
        "detail": (
            "LIFLUCT organizes experiments into regimes defined by sigma (volatility), "
            "toxic_mode, and oracle configuration. A regime family sweeps across multiple "
            "regimes to test whether a fee policy is robust or only works in benign conditions. "
            "Common regimes: low-vol perfect oracle, high-vol lagged oracle, sabotage."
        ),
        "relevance": (
            "The stress_* presets target specific regimes. The advisor suggests a full "
            "regime family (256 runs) once single-regime results are solid. Compare_runs "
            "can identify which regimes cause failure."
        ),
    },
    "oracle": {
        "title": "Price Oracle",
        "short": "The external price feed the AMM uses to detect arbitrage opportunities and set fees.",
        "detail": (
            "The oracle provides the 'true' market price. In perfect mode, the AMM sees "
            "the price instantly. In lagged mode, the oracle is delayed by oracle_lag_steps, "
            "creating a window where arbitrageurs profit from stale prices. "
            "oracle_observation_noise adds noise to the oracle reading. Oracle quality is "
            "the single biggest determinant of LP outcomes."
        ),
        "relevance": (
            "Config fields oracle_mode, oracle_lag_steps, and oracle_observation_noise "
            "control oracle behavior. The stress_oracle_lag preset specifically tests "
            "oracle fragility. Failure modes often cite oracle lag as a root cause."
        ),
    },
}


def list_concepts() -> list[dict[str, str]]:
    """Return a list of all available concepts with title and short description."""
    return [
        {"concept": key, "title": entry["title"], "short": entry["short"]}
        for key, entry in _CONCEPTS.items()
    ]


def explain_concept(concept: str) -> dict[str, Any]:
    """Look up a concept by key. Returns full detail or an error dict."""
    key = concept.strip().lower().replace(" ", "_").replace("-", "_")
    entry = _CONCEPTS.get(key)
    if entry is None:
        available = sorted(_CONCEPTS.keys())
        return {
            "ok": False,
            "error": f"Unknown concept: {concept!r}",
            "available_concepts": available,
        }
    return {"ok": True, "concept": key, **entry}
