# Interpretation: Best-Fixed Search Results

How to read best-fixed search output and compare adaptive policies against the optimized static baseline.

## What the Best Genes Mean

The best-fixed search finds the single set of static gene parameters that maximizes `lp_minus_hodl_b` on the training price path.

### Key gene parameters

- **f_min (minimum fee):** The fee floor. Higher f_min means the AMM always charges at least this much, protecting against toxic flow but potentially deterring volume.
  - If best f_min is very high: the market conditions require aggressive fee protection. Uninformed traders may be priced out.
  - If best f_min is near zero: conditions are benign enough that minimal fees suffice.

- **mu (fee sensitivity):** How aggressively the fee reacts to detected toxic flow. In a static best-fixed search, mu is effectively the fee level since there is no dynamic adjustment.
  - High mu: the optimal strategy is to charge high fees. This usually means toxic flow is significant.
  - Low mu: moderate fees are optimal. Toxic flow is manageable.

- **tau (fee adjustment speed):** How quickly the fee adapts. In static mode, this parameter has limited effect but may influence the fee schedule shape.
  - This parameter is more meaningful for dynamic policies. In best-fixed context, note the value but focus on f_min and mu.

## Train vs. Test Performance Gap

This is the critical overfitting check. The best-fixed search optimizes on a training price path and then evaluates on a held-out test path.

### How to interpret the gap

- **Train performance >> Test performance (large gap):** The best-fixed policy overfit to the training path. The optimal fee for this specific price sequence does not generalize. This is expected to some degree, but large gaps (>50% drop) indicate a noisy or adversarial training environment.

- **Train performance ~ Test performance (small gap):** The optimal static fee generalizes well. This means market conditions are relatively stable across paths, and a fixed fee is a robust strategy.

- **Test performance negative (even if train is positive):** The static policy cannot generalize. This is actually good news for dynamic policies -- it suggests that adaptivity is genuinely needed because no single fixed fee works across conditions.

### Judgment criteria

- Train-test gap < 20%: strong generalization. The best-fixed baseline is credible.
- Train-test gap 20-50%: moderate overfitting. The best-fixed baseline is somewhat inflated.
- Train-test gap > 50%: severe overfitting. The best-fixed number should be discounted.

## Comparing Adaptive vs. Best-Fixed

This is the definitive test: does the adaptive policy beat the best possible static fee?

### Adaptive policy beats best-fixed on test set

"The dynamic fee outperformed even the optimal static fee by {delta} on the test set. This confirms that adaptivity adds genuine value -- no single constant fee can match the dynamic policy's ability to adjust to changing conditions."

This is the strongest possible endorsement of a dynamic policy.

### Adaptive policy beats best-fixed on train but loses on test

"The dynamic fee beat the best-fixed on the training data but lost on the test set. This suggests the dynamic policy is overfitting to the specific training conditions rather than learning generalizable adaptive behavior. The complexity cost is not justified."

### Adaptive policy loses to best-fixed on both

"The dynamic fee underperformed the optimal static fee on both training and test sets. A simple constant fee at {best_f_min} would produce better results. The dynamic mechanism is actively harmful -- it is making worse decisions than doing nothing."

This is a clear signal to simplify: use a static fee at the best-fixed level.

### Adaptive policy close to best-fixed (within margin)

"The dynamic fee and best-fixed policy produce similar results (delta = {small}). The adaptive mechanism is not adding meaningful value over a well-chosen constant fee. Consider whether the complexity is justified by other benefits (robustness across regimes, for example)."

When results are close, the tie goes to simplicity unless the dynamic policy shows clear advantages in other dimensions (e.g., cross-regime consistency).

## Search Profile Context

- **Smoke search (8 fee levels):** The best-fixed found here is approximate. If the dynamic policy barely beats it, a serious search might find a better fixed fee that wins.
- **Serious search (128-256 levels):** This is the definitive baseline. If the dynamic policy beats this, the result is credible.

Always note which search profile was used. "This comparison used a {smoke/serious} best-fixed search. {If smoke: 'A serious search might find a stronger baseline -- consider running one if the margin is small.'}"
