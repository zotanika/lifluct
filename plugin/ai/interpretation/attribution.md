# Interpretation: Attribution Robustness

How to read attribution robustness results and determine whether a policy's advantage is real or an artifact of the measurement method.

## What Attribution Robustness Tests

LIFLUCT can evaluate the same simulation trace under multiple attribution modes. Each mode uses a different reference price to calculate how much each trade cost or earned for the LP:

- **observed_spot:** Uses the current pool price. The default and most intuitive mode.
- **lagged:** Uses a past price, modeling delayed observation of true costs.
- **twap:** Uses a time-weighted average price, smoothing out short-term noise.
- **delayed_reference:** Uses a future price (hindsight evaluation). The harshest assessment.

If a policy looks good under all modes, the result is robust. If it only looks good under one mode, the result is fragile.

## What Rank Correlation Means

The `attribution_ranking_stability.json` output includes Spearman rank correlations between attribution modes. This measures whether the relative ordering of policies (or cells, or epochs) stays the same across modes.

### Interpretation

- **Correlation > 0.8:** Strong agreement. Rankings are consistent regardless of how you measure trade costs. High confidence in the result.
- **Correlation 0.5 -- 0.8:** Moderate agreement. Most rankings agree, but some swap positions. Investigate which specific rankings flip and whether they matter for the conclusion.
- **Correlation 0.2 -- 0.5:** Weak agreement. Many rankings change across modes. The conclusion is unreliable.
- **Correlation < 0.2 or negative:** No agreement. The result is essentially meaningless -- it depends entirely on the measurement method.

### What to report

"Attribution robustness: rank correlation between modes ranges from {min} to {max}. {Interpretation based on the range.}"

## When Rankings Flip

A ranking flip means: Run A beats Run B under mode X, but Run B beats Run A under mode Y. This is the most dangerous finding.

### How to detect

Compare `lp_minus_hodl_b` across modes in `attribution_mode_comparison.json`. If the sign or relative ordering changes:

1. Identify which modes agree and which disagree.
2. Note the magnitude of the flip. A tiny flip (both near zero) is less concerning than a large flip (positive under one mode, significantly negative under another).
3. Check whether the flip involves the primary metric (`lp_minus_hodl_b`) or secondary metrics only.

### How to report

"Rankings flip between {mode_1} and {mode_2} attribution. Under {mode_1}, the policy shows lp_minus_hodl_b = {positive_value}. Under {mode_2}, it shows lp_minus_hodl_b = {negative_value}. The positive result should not be trusted as definitive."

If rankings are stable: "Rankings are consistent across all {N} attribution modes tested. The result is robust to measurement methodology."

## Which Attribution Mode to Trust

No single mode is objectively "correct." Each captures a different aspect of trade cost:

- **observed_spot** is the most intuitive but can be gamed by policies that manipulate the pool price.
- **twap** is more stable and harder to game, but smooths out real short-term dynamics.
- **delayed_reference** is the harshest test -- it evaluates trades with hindsight. If a policy looks good under delayed_reference, the result is very credible.
- **lagged** models realistic conditions where observation itself has latency.

### Recommendation

When modes disagree:
- If the policy is positive under `delayed_reference` and `twap`, trust the positive result. These are the harder tests.
- If the policy is only positive under `observed_spot` and negative under all others, do not trust the positive result. The "Positive but fragile" trap pattern likely applies.
- If unsure, report the range: "lp_minus_hodl_b ranges from {worst_mode_value} to {best_mode_value} depending on attribution mode. The result is {conclusive/inconclusive}."

## Integration with Other Interpretation Templates

Attribution robustness should be checked:
- After any single run interpretation (single_run.md) where the result is precarious.
- During comparison (comparison.md) when the winner's margin is small.
- After best-fixed comparison (best_fixed.md) to verify the adaptive advantage holds.
- During regime family adjudication (regime_family.md) for any regime classified as "Stressed."

Always note whether attribution data was available: "Attribution robustness data {was/was not} available for this run. {If not: 'Consider re-running with multi-mode attribution enabled for higher confidence.'}"
