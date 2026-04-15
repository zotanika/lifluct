# Interpretation: Regime Family Results

How to read results from a multi-regime evaluation and produce an overall adjudication.

## Per-Regime Breakdown

For each regime in the family, classify the result:

### Classification

- **Survived:** `lp_minus_hodl_b > 0`, no critical or high-severity failure modes, attributed loss ratio < 0.5.
- **Stressed:** `lp_minus_hodl_b > 0` but with warnings (attributed loss ratio 0.5-0.8, or medium-severity failure modes present).
- **Failed:** `lp_minus_hodl_b < 0`, or critical/high-severity failure modes detected.

### Per-regime narrative

For each regime, report:
1. The classification (Survived / Stressed / Failed).
2. The `lp_minus_hodl_b` value.
3. The attributed loss ratio.
4. Any failure modes.
5. One sentence on the key driver of the result.

Example: "**Oracle Lag (lag=3):** Stressed. lp_minus_hodl_b = +42, but attributed loss consumes 72% of revenue. The fee compensates for lag, but barely."

## Cross-Regime Consistency Check

After classifying each regime, assess overall consistency.

### Consistency metrics

- **Best regime result:** the highest `lp_minus_hodl_b` across regimes.
- **Worst regime result:** the lowest `lp_minus_hodl_b`.
- **Spread:** best minus worst. Large spreads indicate condition sensitivity.
- **Survival rate:** how many regimes classified as Survived or Stressed vs. Failed.

### Interpretation

- **All Survived:** The policy is robust across tested conditions. This is the best outcome.
- **Mostly Survived (1 failure):** The policy has a specific vulnerability. Identify the failing regime and its root cause. The policy may still be viable if the failing regime is unlikely in practice.
- **Mixed (2+ failures):** The policy is fragile. It only works under favorable conditions. Fundamental redesign needed for broader applicability.
- **All Failed:** The policy is not viable. Start over with simpler conditions (first_run wizard).

## Downside Frequency Analysis

For multi-seed evaluations within each regime:

1. Count how many seeds produced negative `lp_minus_hodl_b` per regime.
2. A regime where 1/16 seeds fails is mildly concerning. Where 4/16 seeds fail is seriously fragile.
3. Report as: "In the oracle lag regime, {N}/16 seeds produced negative LP returns."

### Downside magnitude

- Report the worst single-seed result and the average.
- If the worst seed is dramatically worse than the average, the policy has tail risk.

## Adjudication

Based on the cross-regime assessment, issue one of four verdicts:

### Survives

"The policy survives across all tested regimes with healthy margins. No critical failure modes detected. The result is consistent enough to proceed to deeper evaluation (best-fixed comparison, attribution robustness)."

Use when: all regimes Survived, spread is moderate, no failure modes.

### Mixed

"The policy performs well under {N} regimes but struggles or fails under {M}. Specifically, it breaks under [regime names]. The vulnerability is [root cause]. This policy is viable for environments matching the surviving regimes but should not be deployed where [failing conditions] are possible."

Use when: some regimes Survived, some Failed.

### Fails

"The policy fails across most tested regimes. Only [regime name] produced positive results, and even there [caveats]. The policy design needs fundamental changes before further evaluation is worthwhile."

Use when: most regimes Failed.

### Inconclusive

"Results are too mixed or too close to call. The policy shows borderline performance across regimes, with small positive and small negative results. More data is needed -- consider running additional seeds per regime to separate signal from noise."

Use when: results are near-zero across regimes, or high variance within regimes makes classification unclear.

## Suggested Next Steps by Verdict

- **Survives:** "Run a best-fixed search under the hardest surviving regime to benchmark against the optimal static fee."
- **Mixed:** "Focus on the failing regime. Adjust parameters to address the specific vulnerability and re-test."
- **Fails:** "Simplify: test a single regime with gentler conditions to find a working baseline, then gradually increase stress."
- **Inconclusive:** "Run more seeds (16 per regime) to reduce variance and clarify the signal."
