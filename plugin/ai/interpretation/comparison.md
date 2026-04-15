# Interpretation: Run Comparison

How to compare multiple runs and present a clear verdict.

## Side-by-Side Metric Table

Construct a comparison table with these columns in this order:

| Metric | Run A | Run B | Delta | Winner |
|--------|-------|-------|-------|--------|
| lp_minus_hodl_b | ... | ... | ... | ... |
| total_lp_revenue_b | ... | ... | ... | ... |
| total_attributed_loss_b | ... | ... | ... | ... |
| loss/revenue ratio | ... | ... | ... | ... |
| total_trader_cost_b | ... | ... | ... | ... |
| total_arbitrage_profit_b | ... | ... | ... | ... |
| num_trades (noise/arb) | ... | ... | ... | ... |
| failure_modes | ... | ... | -- | -- |

For 3+ runs, add a column per run and a "Best" column.

## Winner Determination

### Primary metric: lp_minus_hodl_b

The run with the highest `lp_minus_hodl_b` is the primary winner. If multiple runs have the same sign, the magnitude determines the winner.

### Secondary checks before declaring winner

Even if Run A has a higher `lp_minus_hodl_b`, check:

1. **Loss/revenue ratio:** Does the winner have a healthier ratio? If the winner has lp_minus_hodl > 0 but loss/revenue > 0.8, while the runner-up has a lower lp_minus_hodl but loss/revenue < 0.3, flag this. The winner is precarious.

2. **Trader cost:** Does the winner achieve its result through unreasonably high trader costs? If `total_trader_cost_b` for the winner is much higher, flag the "high revenue trap" pattern.

3. **Failure modes:** Does the winner have failure modes that the runner-up does not? A win with structural problems is less trustworthy than a slightly smaller win that is clean.

4. **Trade composition:** Does the winner have a healthier noise/arb ratio? A win driven by extracting fees from a pool dominated by arbitrage is fragile.

## Attribution Robustness Cross-Check

If attribution robustness data is available for any run:

1. Check whether the winner still wins under alternative attribution modes.
2. If rankings flip under a different mode: "The comparison is inconclusive. Run A wins under {mode_1} attribution, but Run B wins under {mode_2}. The result depends on how you measure trade costs."
3. Report the rank correlation if available.

## Pattern and Trap Check

Cross-reference all runs against:
- `patterns/red_flags.md` for danger patterns in the winning run.
- `patterns/traps.md` for false-positive traps.

Specific traps to watch in comparisons:
- "High revenue trap": Winner has much higher revenue AND much higher trader cost. The revenue comes from punitive fees.
- "Perfect oracle hero": Winner only wins because it was tested with a perfect oracle. Check the oracle_mode for each run.
- "Single seed miracle": If comparing runs with different seeds, one great result among many mediocre ones is noise.

## Verdict Construction

### Clear winner

"Run {A} outperforms Run {B} by {delta} on lp_minus_hodl_b. The advantage is supported by {better loss/revenue ratio | lower trader cost | cleaner trade mix}. {Attribution robustness note if available.}"

### Winner with caveats

"Run {A} has a higher lp_minus_hodl_b, but {caveat: high trader cost / precarious loss ratio / failure modes / attribution fragility}. The advantage should be treated as tentative until {next check: stress test / attribution check / multi-seed evaluation}."

### No clear winner

"The runs are too close to call on lp_minus_hodl_b (delta = {small amount}). Run {A} is better on {metrics}, while Run {B} is better on {other metrics}. The choice depends on whether you prioritize {LP returns vs. sustainability vs. robustness}."

### Both failed

"Neither run produced a viable result. Both show negative lp_minus_hodl_b. {Diagnose the shared failure cause.} Consider adjusting {parameters} before re-testing."
