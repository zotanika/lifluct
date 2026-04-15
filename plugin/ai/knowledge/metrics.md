# Key Metrics Reference

For each metric: what it measures, how to judge it, and what warning signs to watch for.

All metrics with the `_b` suffix are denominated in the base asset (asset B, typically the numeraire/stablecoin).

---

## lp_minus_hodl_b

**Definition:** Final LP portfolio value minus the value the LP would have had by simply holding the initial assets without providing liquidity. This is the headline metric.

**Interpretation:**
- Positive: market making beat holding. The fee policy earned its keep.
- Negative: the LP would have been better off doing nothing. The policy failed.
- Zero or near-zero: the policy broke even. Complexity was not rewarded.

**Judgment criteria:**
- Healthy: `lp_minus_hodl_b > 0` AND `total_attributed_loss_b < total_lp_revenue_b * 0.5`
- Precarious: `lp_minus_hodl_b > 0` AND `total_attributed_loss_b > total_lp_revenue_b * 0.8`
- Failed: `lp_minus_hodl_b < 0`

**Warning signs:** A positive value with high attributed loss relative to revenue is fragile. The margin is thin and could flip negative under slightly different conditions. Always check attribution robustness when the ratio exceeds 0.5.

---

## total_lp_revenue_b

**Definition:** Cumulative fee income earned by the LP across all trades during the simulation.

**Interpretation:** This is the gross income side. Revenue alone does not determine success -- what matters is revenue minus losses. But extremely low revenue (relative to TVL and trade volume) signals that fees are set too low.

**Judgment criteria:**
- Compare against `total_attributed_loss_b`: revenue should comfortably exceed loss.
- Compare against `total_trader_cost_b`: if revenue comes from very high trader costs, the fees may be unsustainable in practice (traders would leave).

**Warning signs:** Revenue that is high but driven by a small number of large trades is volatile. Revenue that depends on a specific attribution mode may be an artifact.

---

## total_attributed_loss_b

**Definition:** Heuristic estimate of the MEV (Maximal Extractable Value) cost borne by the LP. Measures how much value was lost to informed/toxic trading.

**Interpretation:** This is the cost side. It estimates how much the LP lost to traders who had better price information. The attribution mode determines how this cost is calculated.

**Judgment criteria:**
- Healthy: well below revenue (`attributed_loss < revenue * 0.5`)
- Concerning: approaching revenue (`attributed_loss > revenue * 0.8`)
- Critical: exceeding revenue (`attributed_loss > revenue`)

**Warning signs:**
- If attributed loss exceeds revenue, the fee policy is not compensating for adverse selection.
- If attributed loss varies wildly across attribution modes, the measurement itself is unreliable. Check `attribution_mode_comparison.json` for robustness.

---

## total_trader_cost_b

**Definition:** Total cost to traders from fees and slippage across all trades.

**Interpretation:** This measures the burden placed on traders. In simulation, traders always trade. In reality, excessive costs drive traders away, killing volume and revenue.

**Judgment criteria:**
- Sustainable: trader cost is moderate relative to trade volume. Traders are paying reasonable fees.
- Unsustainable: trader cost is very high relative to volume. In a real market, traders would route elsewhere.

**Warning signs:**
- Extremely high trader cost with high LP revenue is the "high revenue trap" -- the policy would not survive contact with real markets where traders have alternatives.
- If `total_trader_cost_b` is disproportionately higher than `total_lp_revenue_b`, something is structurally off (e.g., excessive slippage from thin reserves).

---

## total_arbitrage_profit_b

**Definition:** How much value arbitrageurs extracted from the pool across all arbitrage trades.

**Interpretation:** Arbitrage profit is the direct cost of price misalignment. Higher arbitrage profit means the AMM was more frequently and more severely mispriced relative to the external market.

**Judgment criteria:**
- Low relative to revenue: the fee policy is adequately pricing the arbitrage risk.
- High relative to revenue: arbitrageurs are extracting most of the value. The fee is too low to deter toxic flow.

**Warning signs:** If arbitrage profit significantly exceeds LP revenue, the pool is a value-extraction target, not a functioning market.

---

## num_trades (Noise vs. Arbitrage Ratio)

**Definition:** Count of trades broken down by type: noise (uninformed) trades and arbitrage (informed) trades.

**Interpretation:** A healthy pool has a mix of both, with noise trades dominating. Noise trades are the LP's revenue source. Arbitrage trades are the LP's cost.

**Judgment criteria:**
- Healthy: noise trades significantly outnumber arbitrage trades (e.g., 70%+ noise).
- Concerning: arbitrage trades approach or exceed noise trades.
- Toxic: arbitrage trades > 90% of total. The pool exists primarily for value extraction.

**Warning signs:**
- If arb trades dominate, even positive LP returns may be unstable. The pool's "revenue" comes from a thin margin on top of massive extraction.
- Zero or very few total trades indicates a dead pool (see `dead_volume_equilibrium`).

---

## oscillation_score

**Definition:** Measures convergence failure in evolutionary optimization. Tracks how much gene parameters swing between epochs rather than settling.

**Interpretation:** Low oscillation means evolution is converging on a solution. High oscillation means the system cannot find a stable strategy.

**Judgment criteria:**
- Healthy: < 1.0 (converging)
- Warning: 1.0 - 2.0 (noisy convergence)
- Failed: >= 2.0 (no convergence, triggers `no_convergence_oscillation` failure mode)

**Warning signs:** High oscillation combined with mediocre LP returns means the adaptive system is thrashing. Consider increasing `epoch_length`, reducing mutation rate, or simplifying the search space.

---

## dead_volume_score

**Definition:** Measures volume collapse relative to expected trading activity. Compares actual trade volume against what the market conditions should have produced.

**Interpretation:** A score near 1.0 means volume matches expectations. Scores above 1.0 indicate volume suppression -- the fee policy is so aggressive that it choked off trading.

**Judgment criteria:**
- Healthy: < 0.8 (normal volume)
- Warning: 0.8 - 1.0 (volume declining)
- Critical: >= 1.1 (dead pool, triggers `dead_volume_equilibrium` failure mode)

**Warning signs:** A dead volume score near 1.0 with positive LP returns is misleading. The LP looks profitable only because no one is trading (and thus no one is extracting value). This would fail immediately in a live environment with real volume.
