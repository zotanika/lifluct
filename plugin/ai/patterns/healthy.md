# Healthy Patterns

Patterns that indicate genuinely good results. When you see these signatures, the policy is working as intended.

---

## Sustainable Margin

### Signature
- `lp_minus_hodl_b`: positive
- `total_attributed_loss_b < total_lp_revenue_b * 0.3`
- `total_trader_cost_b`: moderate (not extreme relative to volume)
- No failure modes detected
- Trade mix: 60%+ noise trades

### Diagnosis
The fee policy earns substantial revenue while keeping attributed losses well below income. Trader costs are reasonable enough that real-world volume would persist. The pool serves genuine liquidity demand (majority noise trades), not just arbitrage extraction.

This is the ideal operating point: profitable for LPs, usable for traders, resilient against toxic flow.

### AI Response Guide
"This is a strong result. The policy earns a healthy margin with revenue comfortably exceeding attributed losses (ratio: {ratio}). Trader costs are sustainable, and the trade mix shows genuine liquidity demand. Next step: verify this holds under stress conditions (lagged oracle, higher volatility) to confirm robustness."

---

## Robust Across Regimes

### Signature
- `lp_minus_hodl_b`: positive in 3 or more distinct regimes
- No critical failure modes in any regime
- Spread between best and worst regime is less than 50% of the best result
- Attributed loss ratio < 0.5 in all surviving regimes

### Diagnosis
The policy works across a range of market conditions, not just the easy ones. It handles oracle imperfection, elevated volatility, and adversarial trading without collapsing. The consistency across regimes is a stronger signal than any single exceptional result.

A policy that is modestly positive everywhere is more valuable than one that is spectacularly positive in one regime and negative in others.

### AI Response Guide
"This policy shows genuine robustness. It survived {N}/{M} regimes with consistent positive results and no critical failures. The spread between best and worst regime is {spread}, indicating low condition sensitivity. This is a credible candidate for deeper evaluation: run a best-fixed comparison under the hardest surviving regime."

---

## Attribution-Stable

### Signature
- Rank correlation > 0.8 across all tested attribution modes
- `lp_minus_hodl_b` remains positive under all modes
- Sign and relative ordering do not flip between modes
- `delayed_reference` mode also shows positive result

### Diagnosis
The policy's advantage is not an artifact of how trade costs are measured. Whether you use spot prices, time-weighted averages, or hindsight reference prices, the policy still earns its keep. This is a strong quality signal because many policies that look good under one mode fail under others.

The `delayed_reference` mode is particularly demanding -- positive results here mean the policy made good decisions even when evaluated with perfect hindsight.

### AI Response Guide
"Attribution robustness confirms this result. The policy's advantage holds across all {N} attribution modes with rank correlations above 0.8. Even under the strictest mode (delayed_reference), lp_minus_hodl_b remains positive at {value}. This gives high confidence that the result reflects genuine policy quality, not a measurement artifact."

---

## Clean Evolution Convergence

### Signature
- `oscillation_score < 0.5`
- Gene parameters settled to stable values by mid-simulation
- No `gene_collapse_to_bounds` failure mode
- Multiple cells active with differentiated parameters
- `lp_minus_hodl_b` positive

### Diagnosis
In multi-cell turgor mode, the evolutionary process worked as designed. Cells explored different strategies, converged on effective parameters without oscillating or collapsing to bounds, and maintained diversity. The final gene values represent a discovered optimum, not a random walk.

### AI Response Guide
"The evolutionary process converged cleanly (oscillation score: {score}). Gene parameters settled to stable values with {N} active cells maintaining differentiated strategies. This suggests the parameter space is well-configured and the epoch length provides sufficient signal for fitness evaluation."
