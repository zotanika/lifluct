# Failure Modes Reference

LIFLUCT's detection system identifies structural problems in simulation results. Each failure mode below includes the trigger condition, severity, practical meaning, and recommended action.

---

## dead_volume_equilibrium

**Severity:** High

**Trigger:** No trades occurred, or `dead_volume_score >= 1.1`.

**What it means:** The pool is effectively dead. Fees are so high or conditions so hostile that no one trades. In a real market, this pool would be abandoned.

**Why it happens:** Usually caused by fees set too aggressively (`f_min` too high), extreme volatility that makes all trades unprofitable for the trader, or a combination where the dynamic fee overreacts and prices out all activity.

**Recommended action:**
- Lower `f_min` to reduce the fee floor.
- If using dynamic fees, reduce `mu` (fee sensitivity) to make the fee less reactive.
- Check if `sigma` (volatility) is set unrealistically high.
- Compare against a static baseline to determine if the dynamic fee is the cause.

---

## inactive_cell_pathology

**Severity:** Medium

**Trigger:** More than 50% of cells have negligible volume (receiving almost no trades).

**What it means:** Policy diversity failed. Most cells are not contributing. The routing mechanism is concentrating all volume on a few cells while the rest sit idle.

**Why it happens:** One or two cells may have much better parameters, causing the weighted routing to starve the others. Alternatively, initial gene parameters may be poorly distributed.

**Recommended action:**
- Enable or tune lysis to remove dead cells and reallocate capacity.
- Review initial gene parameter ranges -- they may be too narrow or too wide.
- Consider reducing `num_cells` if most are inactive anyway.
- Check if `user_routing_mode` is concentrating traffic too aggressively.

---

## lysis_cascade

**Severity:** High

**Trigger:** 50% or more of cells were lysed (deactivated) in a single epoch.

**What it means:** The safety mechanism triggered mass shutdown. Half or more of the policy population was killed simultaneously, indicating a systemic failure rather than isolated underperformance.

**Why it happens:** A sudden adverse event (price shock, oracle failure) can cause most cells to underperform simultaneously. If lysis thresholds (`kappa`) are too tight, even moderate stress triggers cascading removal.

**Recommended action:**
- Increase `kappa` (lysis threshold) to make lysis less aggressive.
- Switch from `hard` to `soft` lysis mode for gradual penalty instead of instant removal.
- Investigate whether the epoch where the cascade occurred coincides with an extreme market event.
- Consider whether the cell population had sufficient diversity before the cascade.

---

## gene_collapse_to_bounds

**Severity:** Medium

**Trigger:** 50% or more of gene parameters across cells have hit their parameter bounds (minimum or maximum allowed values).

**What it means:** The search space is too narrow. Evolution is trying to push parameters beyond the allowed range, suggesting the optimal values lie outside the bounds you defined.

**Why it happens:** Default parameter ranges may not cover the conditions being tested. For example, high-volatility regimes may need higher `f_min` than the default upper bound allows.

**Recommended action:**
- Widen the parameter bounds for genes that are hitting limits.
- Check which specific genes are collapsing: `f_min` at max suggests fees should be higher; `mu` at max suggests the fee needs more sensitivity.
- Run a broader best-fixed search to understand the landscape before constraining evolution.

---

## no_convergence_oscillation

**Severity:** Medium

**Trigger:** `oscillation_score >= 2.0`.

**What it means:** Evolution is not converging. Gene parameters swing back and forth between epochs instead of settling on a stable strategy.

**Why it happens:** Fitness signals are too noisy (short epochs, high variance per epoch), mutation rate is too high, or the fitness landscape is genuinely multimodal (multiple local optima pulling in different directions).

**Recommended action:**
- Increase `epoch_length` to give each generation more trades for fitness evaluation.
- Reduce mutation rate to prevent overshooting.
- Run multiple seeds to check if the oscillation is consistent or seed-dependent.
- If oscillation persists across seeds, the problem may be fundamental to the parameter space.

---

## monoculture_dominance

**Severity:** Low

**Trigger:** A single cell handles 75% or more of total volume for at least 50% of epochs.

**What it means:** One cell dominates everything. There is no effective diversity. The multi-cell system has collapsed to a single-cell system in practice.

**Why it matters:** While the dominant cell may be performing well, the lack of diversity means the system has no backup strategies. If conditions change, it cannot adapt.

**Recommended action:**
- This is informational if the dominant cell performs well. Note it but do not panic.
- If performance is mediocre, the system failed to explore alternatives. Consider rerunning with different initial gene distributions.
- Compare against a single-cell run to check if multi-cell adds any value here.

---

## oracle_fragility

**Severity:** High

**Trigger:** Oracle stress is present (lagged or noisy oracle) AND LP underperformance detected AND `total_attributed_loss_b > total_lp_revenue_b`.

**What it means:** The policy cannot handle oracle imperfection. When the oracle is anything less than perfect, losses exceed revenue and the LP loses money.

**Why it happens:** The dynamic fee relies on oracle information to detect toxic flow. When the oracle is delayed or noisy, the fee reacts too late or incorrectly, allowing arbitrageurs to extract value during the information gap.

**Recommended action:**
- Increase `f_min` to provide a higher fee floor that protects during oracle gaps.
- Increase `mu` to make the fee more responsive to detected toxic flow.
- Test with progressively increasing `oracle_lag_steps` (1, 2, 3, 5) to find the fragility boundary.
- Consider whether the policy design fundamentally requires better oracle quality than is realistic.

---

## all_cells_inactive_shutdown

**Severity:** Critical

**Trigger:** All cells are inactive in the trailing 20% of the simulation run.

**What it means:** Complete system failure. Every policy cell was deactivated, and no trading occurred in the final portion of the simulation.

**Why it happens:** Usually the end result of a lysis cascade that was not recovered from. Can also occur if extreme market conditions made all strategies unprofitable simultaneously.

**Recommended action:**
- This is the most severe failure. Review the entire run for preceding warning signs (cascading lysis, volume collapse).
- Disable lysis (`lysis_mode: off`) and rerun to see if the underlying policy has any viability.
- If the policy works without lysis but fails with it, the lysis thresholds are too aggressive for the conditions.
- Consider fundamentally different policy parameters or a simpler single-cell approach.
