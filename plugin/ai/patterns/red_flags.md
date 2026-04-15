# Red Flag Patterns

Danger patterns that indicate structural problems. When you see these signatures, flag them prominently in the interpretation.

---

## Loss Exceeds Revenue

### Signature
- `total_attributed_loss_b > total_lp_revenue_b`
- `lp_minus_hodl_b`: typically negative, but can be misleadingly positive in some edge cases
- Attributed loss ratio > 1.0

### Diagnosis
The fee policy is not compensating for adverse selection. Informed traders are extracting more value from the pool than the fee schedule collects from all traders combined. The AMM is a net value transfer mechanism from LPs to arbitrageurs.

If `lp_minus_hodl_b` is somehow positive despite this (can happen with favorable price paths), it is due to the underlying asset appreciation, not the fee policy. This will not persist.

### AI Response Guide
"Critical: attributed losses exceed fee revenue (ratio: {ratio}). The fee policy is structurally insufficient -- it cannot compensate for the toxic flow in these conditions. Increasing f_min or mu is necessary. If using a lagged oracle, consider whether the lag window is simply too large for this fee design to handle."

---

## All Cells Dead/Inactive

### Signature
- `all_cells_inactive_shutdown` failure mode detected
- OR `inactive_cell_pathology` with > 80% inactive cells
- `num_trades`: very low or zero in late epochs
- `dead_volume_score` >= 1.1

### Diagnosis
The system has collapsed. No policy cells are functioning, no trades are occurring. This can result from cascading lysis (all cells killed), extreme fee levels (no one will trade), or catastrophic market conditions that made every strategy unprofitable.

### AI Response Guide
"Critical failure: all policy cells are inactive. The system shut down completely. This is the most severe outcome. Immediate actions: (1) Disable lysis and rerun to check if the underlying policy is viable at all. (2) If it works without lysis, the lysis thresholds (kappa) are too aggressive. (3) If it still fails without lysis, the policy parameters need fundamental revision."

---

## Oracle Fragility Combo

### Signature
- `oracle_fragility` failure mode detected
- `oracle_mode`: lagged or noisy (not perfect)
- `lp_minus_hodl_b`: negative
- `total_attributed_loss_b > total_lp_revenue_b`
- The same policy with `oracle_mode: perfect` produces positive results

### Diagnosis
The policy depends on oracle quality to function. When oracle information degrades (even slightly), the fee cannot react fast enough to protect the LP from toxic flow during the information gap. This is the most common failure pattern for dynamic fee policies.

### AI Response Guide
"Oracle fragility detected. The policy works with perfect oracle (lp_minus_hodl = {perfect_value}) but collapses with {oracle_mode} oracle at lag={lag_steps} (lp_minus_hodl = {lagged_value}). The dynamic fee depends on timely oracle information that is not available in practice. Options: (1) Increase f_min to provide a higher fee floor during oracle gaps. (2) Increase mu for more aggressive fee response. (3) Accept that this policy design requires oracle quality better than {lag_steps} steps lag."

---

## Volume Collapse

### Signature
- `dead_volume_score > 1.0`
- `num_trades`: significantly below expected for the given sigma and num_steps
- `total_trader_cost_b`: very high relative to remaining trades
- `lp_minus_hodl_b`: may be misleadingly near-zero or even slightly positive

### Diagnosis
The fee policy choked off trading activity. Fees are so high that traders stopped participating. The pool looks "safe" (low losses) but only because nothing is happening. In a live market, this pool would be abandoned for cheaper alternatives.

A slightly positive `lp_minus_hodl_b` here is meaningless -- the LP "beat" HODL by doing nothing, with no trades to generate either revenue or loss.

### AI Response Guide
"Warning: volume collapse detected (dead_volume_score = {score}). The fee policy is pricing out trades. Only {num_trades} occurred against an expected {expected}. The {lp_minus_hodl_b} result is not meaningful because the pool is effectively inactive. Reduce f_min to allow more trading activity."

---

## Extreme Arbitrage Dominance

### Signature
- Arbitrage trades > 90% of total trades
- `total_arbitrage_profit_b >> total_lp_revenue_b`
- Noise trades negligible
- `lp_minus_hodl_b`: usually negative, but can be marginally positive

### Diagnosis
The pool exists primarily as a value extraction target for arbitrageurs. Genuine liquidity seekers are absent (or their contribution is negligible). The fee is too low to deter arbitrage, or the oracle lag creates such persistent mispricings that arbitrage is overwhelmingly profitable.

Even if `lp_minus_hodl_b` is marginally positive, this composition is unsustainable. In a real market, informed traders would scale up their activity to extract the remaining margin.

### AI Response Guide
"Warning: extreme arbitrage dominance ({arb_pct}% of trades are arbitrage). The pool is functioning as an extraction target, not a functioning market. The fee is insufficient to deter informed traders. Increase f_min significantly, or address the underlying oracle lag that creates the arbitrage opportunity."

---

## Lysis Cascade

### Signature
- `lysis_cascade` failure mode detected
- 50%+ cells lysed in a single epoch
- Often followed by `all_cells_inactive_shutdown` or `inactive_cell_pathology`
- `lp_minus_hodl_b`: usually negative

### Diagnosis
A mass die-off of policy cells occurred in one epoch. This indicates systemic failure rather than isolated underperformance. Typically caused by a sudden adverse event (price shock, oracle failure) that made most strategies simultaneously unprofitable, combined with lysis thresholds that are too tight.

### AI Response Guide
"High severity: a lysis cascade occurred at epoch {epoch}. {N}% of cells were deactivated simultaneously. This indicates that most strategies failed under the same conditions. The lysis threshold (kappa) may be too aggressive for these market conditions. Try (1) switching to soft lysis, (2) increasing kappa, or (3) disabling lysis to observe behavior without the circuit breaker."
