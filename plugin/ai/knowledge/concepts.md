# Domain Concepts

Reference for AI assistants interpreting LIFLUCT experiment results. Each concept includes what it is, why it matters, and how it connects to the numbers you see in output.

---

## AMM (Automated Market Maker)

A smart contract that uses a deterministic pricing formula to provide liquidity, replacing the traditional order book with a bonding curve.

**Why it matters:** LIFLUCT simulates a single AMM pool. Every metric you see measures how well the AMM performed under a given fee policy, oracle configuration, and adversarial environment. The AMM is the system under test.

**Connection to results:** The AMM's reserves, invariant function, and fee schedule determine all output metrics. When `lp_minus_hodl_b` is positive, the AMM's fee policy earned more than the cost of providing liquidity.

---

## LP (Liquidity Provider)

An agent who deposits capital into the AMM pool and earns trading fees in return. LPs bear adverse selection risk: informed traders systematically trade against them when prices move.

**Why it matters:** LP welfare is the primary outcome LIFLUCT measures. The central question is whether the fee policy makes the LP better off than simply holding their initial assets (the HODL benchmark).

**Connection to results:** `lp_minus_hodl_b` is the headline metric. `total_lp_revenue_b` shows fee income. `total_attributed_loss_b` shows what informed trading cost the LP. The difference between revenue and attributed loss determines whether the policy works.

---

## Toxic Flow

Structurally harmful trading patterns that extract value from the pool. When external prices move before the AMM updates, fast traders buy at stale prices and profit from the difference. This is not manipulation; it is a structural feature of how AMMs work.

**Why it matters:** Toxic flow is the primary threat to LP profitability. A fee policy must either deter toxic flow (by raising fees when it is likely) or earn enough from uninformed flow to offset the damage.

**Connection to results:** `total_attributed_loss_b` quantifies the cost of toxic flow. `total_arbitrage_profit_b` shows how much arbitrageurs extracted. The ratio of arbitrage trades to noise trades in `num_trades` reveals whether the pool is dominated by extractors. LIFLUCT's `toxic_mode` config controls adversary behavior: `cheapest_active` (baseline), `fee_aware_max_extraction` (realistic), and `sabotage` (worst case).

---

## Attribution

The method used to measure how much value each trade cost or earned for LPs. Different reference prices produce different answers.

**Why it matters:** If a policy only looks good under one attribution mode but fails under others, the conclusion is fragile. Attribution robustness is a second-order quality check that separates genuinely strong results from lucky ones.

**Connection to results:** The `attribution_mode` config field selects the primary mode. Available modes:
- `observed_spot` -- uses the current pool price as reference
- `lagged` -- uses a past price, modeling delayed observation
- `twap` -- uses a time-weighted average price
- `delayed_reference` -- uses a future price, modeling hindsight evaluation

The `attribution_mode_comparison.json` and `attribution_ranking_stability.json` outputs show whether conclusions hold across modes.

---

## Best-Fixed Policy

The strongest possible static (constant-fee) policy found by exhaustive search over the same price path. This is the fairest and most demanding comparison baseline.

**Why it matters:** Comparing a dynamic fee policy against a naive static fee is misleading. The best-fixed policy asks: "Could a single well-chosen constant fee have done just as well?" If the answer is yes, the dynamic policy's complexity is not justified.

**Connection to results:** Best-fixed search output includes the optimal gene parameters (`f_min`, `mu`, `tau`) and train/test performance. A dynamic policy should beat the best-fixed on the test set (not just the training set) to demonstrate genuine adaptive value.

---

## Lysis

A circuit breaker that deactivates underperforming policy cells. When a cell's attributed losses exceed a threshold (controlled by `kappa`), lysis triggers.

**Why it matters:** In multi-cell turgor mode, lysis prevents dead-weight cells from diluting pool performance. It is the evolutionary pressure that kills bad strategies.

**Connection to results:** `lysis_mode` controls behavior: `off` (disabled), `soft` (reduce routing weight gradually), `hard` (deactivate immediately). High lysis counts with good LP returns suggest effective evolutionary pressure. A `lysis_cascade` failure mode (50%+ cells lysed in one epoch) means the safety mechanism triggered mass shutdown.

---

## Regime

A specific market condition defined by oracle quality, volatility level, and adversary type. Regimes are the controlled environments used for testing.

**Why it matters:** A policy that only works in benign conditions (low volatility, perfect oracle) is fragile. Regime family evaluation tests across multiple environments to map where a policy succeeds and where it breaks.

**Connection to results:** Common regimes: low-vol perfect oracle (easy), high-vol perfect oracle (harder), lagged oracle (realistic), sabotage (worst case). The `stress_*` presets target specific regimes. Cross-regime consistency is a strong quality signal.

---

## Oracle

An external price feed that tells the AMM what assets are worth on other markets. The oracle's quality is the single biggest determinant of LP outcomes.

**Why it matters:** Real oracles are never perfect. They have latency (lag) and noise. A policy that only works with perfect oracle information will fail in production.

**Connection to results:** Config fields: `oracle_mode` (`perfect`, `lagged`, `noisy`), `oracle_lag_steps` (delay in simulation steps), `oracle_observation_noise` (random error magnitude). The `stress_oracle_lag` preset specifically tests oracle fragility. The `oracle_fragility` failure mode fires when oracle imperfection combined with the policy produces LP losses.

---

## CPMM (Constant Product Market Maker)

The simplest AMM model, using the invariant x * y = k. When one asset is bought, the other becomes relatively more expensive. All trades move along this constant-product curve.

**Why it matters:** CPMM is the baseline AMM model. A static CPMM with a fixed fee is the simplest possible system. Any dynamic or adaptive policy must justify its complexity by outperforming this baseline.

**Connection to results:** The `smoke_static` preset runs a CPMM with fixed fee for baseline comparison. `baseline_type: static_cpmm` in configs selects this model.

---

## Cell

A policy module with gene parameters that define fee behavior. Each cell has its own `f_min` (minimum fee), `mu` (fee sensitivity), `tau` (fee adjustment speed), and `beta` (directional bias).

**Why it matters:** In multi-cell turgor mode, multiple cells compete. Trade routing distributes volume among cells based on fitness. Evolution mutates gene parameters. This creates an adaptive system that discovers effective fee strategies through competition.

**Connection to results:** `num_cells` controls how many cells run in parallel. Gene parameter values appear in best-fixed search output and per-cell diagnostics. When cells cluster around similar parameters, diversity has collapsed (see `monoculture_dominance` failure mode).

---

## Epoch

A fixed-length simulation period (controlled by `epoch_length`) after which evolutionary operations can occur: fitness evaluation, gene mutation, cell reproduction, and lysis.

**Why it matters:** Epochs structure the adaptive process. Too short: noisy fitness signals cause oscillation. Too long: slow adaptation to changing conditions.

**Connection to results:** `epoch_length` in config sets the step count per epoch. The `oscillation_score` metric measures whether evolution is converging or oscillating between epochs. `no_convergence_oscillation` failure mode triggers when oscillation_score >= 2.0.
