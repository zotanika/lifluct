# Stress Test Wizard

## Trigger

Activate when:
- User says "stress test", "worst case", "extreme", "hostile", "how robust", or equivalent.
- User wants to test a policy across multiple difficult conditions.
- User asks "will this survive?" or "what breaks it?"

## Steps

### Step 1: Identify the policy to stress

If user has a config or recent run:
- Use the policy parameters from their config.

If not:
- Ask: "Which policy do you want to stress test? You can provide a config file, specific parameters (f_min, mu, tau), or I can use the default dynamic fee preset."

### Step 2: Generate 4 regime configs

Create four experiment configs using the user's policy parameters under different stress conditions:

**Regime 1 -- Perfect (control):**
- `oracle_mode: perfect`, `oracle_lag_steps: 0`
- `sigma: 0.02`, `toxic_mode: cheapest_active`
- Purpose: best-case baseline to compare against.

**Regime 2 -- Oracle Lag:**
- `oracle_mode: lagged`, `oracle_lag_steps: 3`
- `sigma: 0.03`, `toxic_mode: fee_aware_max_extraction`
- Purpose: tests whether the policy handles delayed price information.

**Regime 3 -- High Volatility:**
- `oracle_mode: perfect`, `oracle_lag_steps: 0`
- `sigma: 0.08`, `toxic_mode: fee_aware_max_extraction`
- Purpose: tests fee responsiveness under extreme price movement.

**Regime 4 -- Sabotage:**
- `oracle_mode: lagged`, `oracle_lag_steps: 2`
- `sigma: 0.03`, `toxic_mode: sabotage`
- Purpose: maximum adversarial pressure. The arbitrageur actively tries to destroy LP value.

Present the four regimes and estimated time:
"I'll test your policy across 4 stress regimes. Each run takes ~2 minutes. Total estimated time: ~8 minutes. The regimes test oracle lag, high volatility, and adversarial sabotage."

Ask: "Ready to run all 4, or would you like to adjust any regime?"

### Step 3: Dispatch parallel runs

Action: Dispatch 4 batch-runner agents, one per regime config.

Each batch-runner:
1. Calls `run_experiment(config=regime_config, label="stress_[regime_name]")`.
2. Calls `read_results(run_id=result_id)`.
3. Returns structured results.

Say: "Running 4 experiments in parallel. I'll report results as they complete."

### Step 4: Collect and compare results

When all 4 runs complete:

Action: Call `compare_runs(run_ids=[r1, r2, r3, r4])`.

Build a regime comparison table:

| Regime | lp_minus_hodl_b | Loss/Revenue Ratio | Failure Modes |
|--------|-----------------|---------------------|---------------|
| Perfect | ... | ... | ... |
| Oracle Lag | ... | ... | ... |
| High Vol | ... | ... | ... |
| Sabotage | ... | ... | ... |

### Step 5: Interpret across regimes

Follow `interpretation/regime_family.md`:

**Per-regime assessment:**
For each regime, classify as Survived (positive lp_minus_hodl, no critical failures), Stressed (positive but precarious), or Failed (negative or critical failures).

**Cross-regime consistency check:**
- Survives all 4: robust policy. Proceed to deeper evaluation.
- Survives 3/4: identify the breaking point. Report which regime failed and why.
- Survives 2/4 or fewer: policy is fragile. Needs fundamental redesign for the failing conditions.

**Downside analysis:**
Report the worst-case result and how far it is from the best-case. Large spreads indicate condition sensitivity.

Check patterns:
- `patterns/red_flags.md` for any danger patterns in surviving regimes.
- `patterns/traps.md` for false-positive traps (e.g., "perfect oracle hero" pattern).

### Step 6: Suggest next steps

Action: Call `suggest_next_experiment` with all 4 runs.

Common recommendations:
- All survived: "Run a best-fixed search under the hardest surviving regime. Estimated time: ~15 minutes."
- 3/4 survived: "The policy breaks under [failing regime]. Try increasing f_min or mu and re-test that specific regime."
- Mixed results: "Consider a full 16-seed evaluation on the 2 regimes that passed, to confirm they are not single-seed flukes. Estimated time: ~1 hour locally."
- All failed: "The policy is not viable under stress. Start with gentler conditions (wizard/first_run.md) and iterate."

## Completion

Report:
- Summary table of all 4 regimes.
- Overall adjudication: Robust / Mostly Robust / Fragile / Failed.
- The specific breaking point (which regime, which metric).
- Pattern/trap warnings if applicable.
- Recommended next experiment with local time estimate.

Example: "Your policy survived 3/4 stress regimes. It handles oracle lag and high volatility well, but collapses under sabotage adversary (lp_minus_hodl_b = -450). The sabotage failure is driven by attributed losses 3x revenue. Next recommended: increase f_min from 0.003 to 0.005 and re-test the sabotage regime (~2 min)."
