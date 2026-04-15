# Trap Patterns (False Positives)

Results that look good on the surface but indicate structural problems. These are more dangerous than outright failures because they can lead to false confidence.

---

## High Revenue Trap

### Signature
- `lp_minus_hodl_b`: positive (often strongly positive)
- `total_lp_revenue_b`: very high
- `total_trader_cost_b`: extremely high (disproportionate to revenue)
- `total_attributed_loss_b`: may be low (because high fees deter most informed traders too)
- `dead_volume_score`: approaching 1.0 but not yet triggering the failure mode

### Diagnosis
The fee policy is set so aggressively that it extracts maximum revenue from every trade that does occur. The LP looks profitable because the few traders who do trade pay enormous costs. But this is an illusion: in a real market with alternative venues, traders would simply go elsewhere. The high revenue depends on captive volume that does not exist in production.

This is the AMM equivalent of a store that charges $100 for a bottle of water. One sale is profitable, but the store is empty.

### AI Response Guide
"Trap pattern detected: High Revenue Trap. The LP result looks positive (lp_minus_hodl = {value}), but this is driven by extremely high trader costs ({total_trader_cost_b}). In a competitive market, this fee level would kill volume entirely. The result is not sustainable in practice.

To test this: reduce f_min and mu by 30-50% and check whether the policy still produces positive results with more reasonable trader costs. If it does not, the policy only 'works' through punitive pricing."

---

## Positive but Fragile

### Signature
- `lp_minus_hodl_b`: positive under `observed_spot` attribution
- `lp_minus_hodl_b`: negative or near-zero under `twap` or `delayed_reference` attribution
- Rank correlation across attribution modes < 0.5
- Attributed loss ratio varies wildly across modes (e.g., 0.3 under observed_spot, 0.9 under twap)

### Diagnosis
The positive result is an artifact of the measurement method, not genuine policy quality. The `observed_spot` mode can be the most generous because it uses the current pool price (which the policy may be manipulating through its fee schedule). When evaluated with more rigorous reference prices (TWAP, delayed), the advantage disappears or reverses.

This is the most common trap for dynamic fee policies that exploit short-term price movements without providing genuine LP protection.

### AI Response Guide
"Trap pattern detected: Positive but Fragile. The lp_minus_hodl result is positive under observed_spot attribution (+{obs_value}) but flips to negative under twap (-{twap_value}) and delayed_reference (-{ref_value}). The positive result should not be trusted.

The policy may be exploiting measurement artifacts rather than providing genuine LP protection. Recommendation: evaluate the policy primarily under twap or delayed_reference attribution. If it is negative under both, the policy needs redesign."

---

## Perfect Oracle Hero

### Signature
- `lp_minus_hodl_b`: strongly positive with `oracle_mode: perfect`
- `lp_minus_hodl_b`: negative or sharply reduced with `oracle_mode: lagged` (even lag=1)
- Performance gap between perfect and lagged oracle > 80%
- `oracle_fragility` failure mode may or may not trigger (depends on whether loss exceeds revenue)

### Diagnosis
The policy's performance depends entirely on having perfect oracle information. It has learned to exploit the perfect price feed to make precise fee adjustments, but this capability breaks down immediately when any oracle latency is introduced. Since real oracles always have some latency, this policy will fail in production.

This is common when developing policies against `oracle_mode: perfect` without testing degraded oracle scenarios.

### AI Response Guide
"Trap pattern detected: Perfect Oracle Hero. The policy performs excellently with a perfect oracle (lp_minus_hodl = {perfect_value}) but collapses with even minimal oracle lag (lag=1: {lag1_value}, lag=3: {lag3_value}).

This is a development artifact. The policy has been optimized for conditions that do not exist in production. Recommendation: (1) Re-develop the policy using lagged oracle (lag=2-3) as the primary test condition. (2) Treat perfect oracle results as an upper bound, not an expected outcome. (3) A policy that is modestly positive with lag=3 is more valuable than one that is spectacularly positive with perfect oracle."

---

## Single Seed Miracle

### Signature
- `lp_minus_hodl_b`: strongly positive on one seed (e.g., seed=42)
- `lp_minus_hodl_b`: negative or much worse on other seeds (seeds 1-16)
- High variance across seeds for the same config
- Result driven by a specific favorable price path rather than policy quality

### Diagnosis
The impressive result is due to luck, not skill. The specific random seed generated a price path that happened to favor this policy. On other price paths, the policy fails. This is overfitting to a single realization of market randomness.

This is particularly dangerous because early development often uses a single seed (seed=42 by convention). A policy can appear to work perfectly on that seed and fail catastrophically on others.

### AI Response Guide
"Trap pattern detected: Single Seed Miracle. The strong result on seed={good_seed} (lp_minus_hodl = {good_value}) does not replicate across other seeds. Results on seeds 1-16: {summary or worst case}.

This indicates the result is path-dependent, not policy-driven. The policy happened to benefit from the specific price movements generated by this seed. Recommendation: always evaluate across at least 4 seeds before drawing conclusions. For serious evaluation, use 16 seeds. The policy's true quality is better estimated by the median across seeds, not the best single result."
