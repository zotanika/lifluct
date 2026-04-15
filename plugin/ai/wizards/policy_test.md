# Policy Test Wizard

## Trigger

Activate when:
- User provides a config file path or config parameters.
- User says "test my policy", "evaluate this config", "run this", or equivalent.
- User has specific fee parameters (f_min, mu, tau) they want to test.

## Steps

### Step 1: Validate the config

If user provided a file path:
- Read the config file.
- Call `validate_config(config)` to check for consistency issues.

If user provided parameters:
- Call `configure_experiment(...)` with the specified parameters and sensible defaults for unspecified ones.
- Call `validate_config(config)` on the result.

Report any validation issues:
- Errors: "This config has problems that need to be fixed before running: [issues]."
- Warnings: "A few notes about this config: [warnings]. These are not blocking, but worth knowing."
- Clean: "Config looks good."

### Step 2: Choose stress level

Ask: "What conditions do you want to test under?
- **Gentle:** Perfect oracle, low volatility (sigma=0.02). Best-case scenario.
- **Realistic:** Lagged oracle (3 steps), moderate volatility (sigma=0.03). Closer to production.
- **Hostile:** Lagged oracle, high volatility, sabotage adversary. Worst case."

Based on response, prepare the run config:
- Gentle: `oracle_mode=perfect, oracle_lag_steps=0, sigma=0.02, toxic_mode=cheapest_active`
- Realistic: `oracle_mode=lagged, oracle_lag_steps=3, sigma=0.03, toxic_mode=fee_aware_max_extraction`
- Hostile: `oracle_mode=lagged, oracle_lag_steps=3, sigma=0.08, toxic_mode=sabotage`

### Step 3: Run the policy and a baseline

Action: Run two experiments:
1. The user's policy config (with chosen stress level overlays).
2. A static CPMM baseline under the same conditions (same seed, same oracle, same volatility).

Say: "Running your policy and a static baseline under [stress level] conditions. This gives us a clean comparison. Estimated time: ~2 minutes for both."

Call `run_experiment(config=user_config, label="policy_test")`.
Call `run_experiment(config=baseline_config, label="baseline_static")`.

### Step 4: Compare and interpret

Action: Call `compare_runs(run_ids=[policy_run_id, baseline_run_id])`.

Follow `interpretation/comparison.md`:
- Build side-by-side metric table.
- Determine winner on `lp_minus_hodl_b`.
- Check attributed loss ratios for both.
- Note trader cost differences.

### Step 5: Check for patterns and traps

Cross-reference results against:
- `patterns/red_flags.md` -- any danger patterns?
- `patterns/traps.md` -- any false-positive traps?

If the policy wins but shows trap signatures (e.g., very high trader cost, attribution fragility), flag it explicitly.

### Step 6: Suggest next steps

Action: Call `suggest_next_experiment` with both runs.

Common recommendations:
- If policy won under gentle conditions: "Test under realistic conditions to check robustness."
- If policy won under realistic conditions: "Run a best-fixed search to confirm the dynamic fee adds value beyond the best static fee."
- If policy lost: "The policy underperformed the static baseline. Consider adjusting [specific parameters based on which metrics were weak]."

## Completion

Report:
- Verdict: "Your policy [beat/lost to] the static baseline by [amount] under [conditions]."
- Key metrics: lp_minus_hodl_b, attributed loss ratio, trader cost.
- Pattern/trap warnings if any.
- Recommended next experiment with time estimate.
