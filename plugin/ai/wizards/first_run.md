# First Run Wizard

## Trigger

Activate when:
- User has no prior runs (empty `list_runs` result).
- User says "start", "help", "first time", "getting started", or equivalent.
- No other intent is detected.

## Steps

### Step 1: Understand the user's goal

Ask: "What would you like to evaluate? For example:
- A specific fee policy you have in mind
- Whether dynamic fees beat static fees for your conditions
- How a policy handles stress conditions
- Just exploring what LIFLUCT can do"

Based on response:
- If they have a specific config file -> exit to `policy_test.md` wizard.
- If they want comparison -> exit to `compare.md` wizard.
- If they want stress testing -> exit to `stress_test.md` wizard.
- If exploring or unsure -> continue to Step 2.

### Step 2: Suggest a smoke test

Say: "Let's start with a quick smoke test to confirm everything works and establish a baseline. This runs a dynamic fee policy under ideal conditions (perfect oracle, low volatility). Takes about 1 minute."

Action: Call `list_presets(category="smoke_test")` to show available smoke presets.

Recommend: `smoke_dynamic` for the first run.

Ask: "Ready to run? Or would you prefer to start with the static CPMM baseline instead?"

### Step 3: Execute the smoke test

Action: Call `run_preset(preset_name="smoke_dynamic")`.

While waiting, briefly explain what is happening: "Running a 400-step simulation with a dynamic fee policy. The AMM uses a constant-product curve (x*y=k) and adjusts fees based on detected toxic flow."

### Step 4: Interpret results

Action: Call `read_results(run_id=<result_run_id>)`.

Follow the interpretation template in `interpretation/single_run.md`:
1. Check failure modes first.
2. Report `lp_minus_hodl_b` verdict (positive/negative).
3. Check attributed loss vs revenue ratio.
4. Note trade composition (noise vs arbitrage).

Present as a concise narrative, not a data dump.

### Step 5: Suggest next steps

Action: Call `suggest_next_experiment` with the completed run.

Present the recommendation with context: "Based on this result, I recommend..."

Typical next steps from a successful smoke test:
- Run `smoke_static` for comparison (1 min).
- Test with lagged oracle to check robustness (2 min).
- Run a 4-regime stress battery (~8 min).

## Completion

Report:
- One-sentence verdict on the smoke test result.
- The recommended next experiment with estimated time.
- A brief explanation of why that next step matters.

If the result was healthy: "Your first run looks solid. The dynamic fee earned more than HODL and attributed losses are well below revenue. Next, I recommend [suggestion] to check if this holds under more realistic conditions."

If the result had issues: "Your first run flagged some concerns: [issues]. Before expanding to more experiments, let's investigate. I recommend [targeted suggestion]."
