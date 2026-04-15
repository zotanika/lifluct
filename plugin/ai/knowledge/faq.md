# Frequently Asked Questions

---

## 1. Why is lp_minus_hodl_b negative?

A negative `lp_minus_hodl_b` means the LP lost money compared to simply holding. The fee income did not cover the cost of adverse selection (informed traders extracting value from the pool).

Common causes:
- **Fees too low:** The fee floor (`f_min`) does not adequately compensate for toxic flow. Try increasing `f_min`.
- **Oracle lag:** With a lagged oracle, arbitrageurs have a window to trade at stale prices. The longer the lag, the worse the damage. Check `oracle_lag_steps`.
- **High volatility:** More price movement means more arbitrage opportunity. If `sigma` is high, fees need to be higher to compensate.
- **Aggressive adversary:** `toxic_mode: sabotage` is the worst case. Not all policies survive it.

Check `total_attributed_loss_b` vs `total_lp_revenue_b`. If loss far exceeds revenue, the fee is structurally insufficient.

---

## 2. What's a good attributed_loss ratio?

The ratio of `total_attributed_loss_b / total_lp_revenue_b` indicates how much of the LP's gross income is consumed by informed trading costs.

- **< 0.3:** Excellent. The policy handles adverse selection well.
- **0.3 -- 0.5:** Healthy. Normal for moderate-stress conditions.
- **0.5 -- 0.8:** Concerning. The margin is thin. Check attribution robustness.
- **> 0.8:** Precarious. Even a small change in conditions could flip `lp_minus_hodl_b` negative.
- **> 1.0:** Failed. Losses exceed revenue.

Always cross-check with attribution robustness. If the ratio looks good under `observed_spot` but bad under `twap`, the result is fragile.

---

## 3. Why are there so many arbitrage trades?

A high proportion of arbitrage trades (relative to noise trades) means the pool is primarily serving value extractors rather than genuine liquidity seekers.

This happens when:
- **Oracle lag creates persistent mispricings.** Arbitrageurs exploit the gap between the oracle price and the true market price.
- **Fees are too low to deter arbitrage.** If the fee is less than the expected profit from price misalignment, rational arbitrageurs will always trade.
- **Volatility is high.** More price movement creates more arbitrage opportunities.

A pool where 90%+ of trades are arbitrage is functioning as an extraction target, not a market. Even if `lp_minus_hodl_b` is positive, this composition is unsustainable in practice.

---

## 4. What does "monoculture_dominance" mean?

This failure mode fires when a single cell handles 75%+ of volume for 50%+ of epochs. The multi-cell system has effectively collapsed to a single-cell system.

**Is it bad?** Not necessarily. If the dominant cell is performing well, the system found a strong strategy and concentrated on it. This is efficient, but fragile -- there are no backup strategies if conditions change.

**What to do:** Compare the multi-cell result against a single-cell run with the dominant cell's parameters. If they perform similarly, the multi-cell overhead is not justified for this scenario. If you want diversity, adjust routing weights or mutation parameters.

---

## 5. Should I use dynamic or static fees?

It depends on what you are testing.

- **Static fees** (`use_dynamic_fee: false`, `baseline_type: static_cpmm`) are simpler and should be your first baseline. They tell you whether any reasonable fee level works for the given conditions.
- **Dynamic fees** (`use_dynamic_fee: true`) adapt based on market signals. They should outperform the best possible static fee. If they do not, the dynamic mechanism is not earning its complexity cost.

Start with a smoke test of both (`smoke_dynamic` and `smoke_static`), then compare. If the dynamic fee wins, run a best-fixed search to check if it also beats the optimized static baseline.

---

## 6. What oracle_lag_steps should I test with?

- **0 (perfect oracle):** Best case. Use for initial smoke tests and establishing upper-bound performance.
- **1-2:** Mild lag. A policy that fails here is extremely fragile.
- **3:** Moderate lag. A reasonable proxy for realistic oracle conditions. The `stress_oracle_lag` preset uses this.
- **5-10:** Severe lag. Tests extreme oracle degradation. Only robust policies survive.

A good progression: run at 0, then 3, then check if the policy still produces positive `lp_minus_hodl_b`. If it collapses at lag=3, try lag=1 and lag=2 to find the fragility boundary.

---

## 7. How do I know if my policy is overfitting?

Signs of overfitting:
- **Single seed success:** Great results on `seed=42` but poor results on seeds 1--16. Always test multiple seeds.
- **Train-test gap in best-fixed search:** If train performance is much better than test performance, the policy is fitting to the specific price path rather than learning generalizable behavior.
- **Perfect oracle dependency:** Excellent results with `oracle_mode: perfect` that collapse with any lag. The policy learned to exploit perfect information rather than being robust.
- **Attribution fragility:** Rankings change across attribution modes. The "advantage" depends on how you measure it.

The strongest overfitting check is a regime family evaluation: test across multiple regimes and multiple seeds. Genuine policy quality shows up as consistency, not as a single spectacular result.

---

## 8. What's the difference between smoke and serious best-fixed search?

- **Smoke profile** (`search_profile: smoke`): Tests 8 fee levels. Fast (~1 minute). Good for quick sanity checks. Tells you whether the dynamic policy is in the right ballpark.
- **Serious profile** (`search_profile: serious`): Tests 128--256 fee levels. Slow (~1--8 hours locally). Finds the true best fixed policy. This is the definitive benchmark.

Start with smoke. If the dynamic policy beats the smoke best-fixed, it is worth running the serious search to confirm. If the dynamic policy loses to even the smoke best-fixed, something is fundamentally wrong.

---

## 9. When should I enable lysis?

Enable lysis when running multi-cell experiments (`num_cells > 1`) where you want evolutionary pressure to remove underperforming strategies.

- **Off:** Use for initial exploration, single-cell runs, and when you want to observe all cells' behavior without culling.
- **Soft:** Start here. Soft lysis reduces routing weight to underperformers rather than killing them. Less risk of cascade.
- **Hard:** Use when you want aggressive culling. Cells are immediately deactivated when they underperform. Risk of lysis cascade if conditions are harsh.

Monitor `total_lysis_count` and watch for the `lysis_cascade` failure mode. If cascades occur, either switch to soft lysis or increase the `kappa` threshold.

---

## 10. How should I interpret attribution robustness?

Attribution robustness tests whether your policy's advantage holds across different methods of calculating trade costs.

**What to check:**
- `attribution_mode_comparison.json`: Shows `lp_minus_hodl_b` and `total_attributed_loss_b` under each attribution mode.
- `attribution_ranking_stability.json`: Shows Spearman rank correlation between modes. Values near 1.0 mean rankings agree. Values near 0 or negative mean they disagree.

**Interpretation:**
- **Rank correlation > 0.8 across all modes:** Robust. The policy's relative performance is consistent regardless of measurement method. Strong confidence in results.
- **Rank correlation 0.5 -- 0.8:** Mixed. Some modes agree, some disagree. Investigate which mode causes the disagreement and why.
- **Rank correlation < 0.5:** Fragile. The policy's "advantage" depends on how you measure it. The result should not be trusted as-is.

If a policy looks positive under `observed_spot` but negative under `twap` or `delayed_reference`, the positive result is likely an artifact of the measurement method, not a genuine advantage.
