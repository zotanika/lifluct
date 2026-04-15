# Comparison Wizard

## Trigger

Activate when:
- User says "compare", "vs", "versus", "side by side", or equivalent.
- User references multiple run IDs or labels.
- User asks "which one is better?" about previous results.

## Steps

### Step 1: Identify runs to compare

Action: Call `list_runs()` to show available runs.

If user specified run IDs or labels: use those directly.

If not: present the list and ask which runs to compare. Group runs by similarity:
- Same config, different seeds -> "These 3 runs test the same policy with different random seeds."
- Same conditions, different policies -> "These 2 runs compare dynamic vs static under identical conditions."
- Different conditions, same policy -> "These 4 runs test the same policy across different stress levels."

Ask: "Which runs would you like to compare? You can specify run IDs, or I can auto-group runs that share similar configs."

### Step 2: Auto-group by similarity

If the user wants auto-grouping, organize runs by:
1. Same `baseline_type` + same `oracle_mode` + same `sigma` -> policy variant comparison.
2. Same policy params + different `oracle_mode` or `sigma` -> stress progression.
3. Same everything + different `seed` -> seed robustness check.

Present the groupings and let the user confirm or adjust.

### Step 3: Run comparison

Action: Call `compare_runs(run_ids=[...])` with the selected runs.

Follow `interpretation/comparison.md` to construct the narrative:
- Build side-by-side metric table.
- Determine winner on primary metric (`lp_minus_hodl_b`).
- Note the margin of victory.
- Check whether the winner is consistent across secondary metrics.

### Step 4: Deep analysis

For each run in the comparison:
- Check attributed loss ratio.
- Check for failure modes.
- Note trade composition differences.

Cross-reference against patterns:
- `patterns/red_flags.md` -- any danger signals in the winning run?
- `patterns/traps.md` -- is the winner a false positive?

If attribution robustness data exists for any run:
- Call `read_attribution_robustness(run_id)`.
- Check if the winner still wins under different attribution modes.
- Report: "The winner holds/flips under alternative attribution methods."

### Step 5: Synthesize verdict

Construct a clear verdict:
- "Run X beats Run Y by [margin] on lp_minus_hodl_b. The advantage is [robust/fragile] across attribution modes."
- If there are caveats: "However, Run X shows [red flag/trap pattern], which means [explanation]."
- If results are mixed: "No clear winner. Run X is better on [metrics], Run Y is better on [other metrics]. The choice depends on whether you prioritize [LP returns vs trader experience vs robustness]."

### Step 6: Suggest next steps

Action: Call `suggest_next_experiment` with all compared runs.

Common recommendations:
- If one policy clearly wins: "Run a best-fixed search to benchmark against the optimal static fee."
- If results are close: "Run both under additional stress conditions to find where they diverge."
- If both fail: "Neither policy is viable under these conditions. Consider adjusting [parameters]."

## Completion

Report:
- Comparison table (concise, key metrics only).
- Verdict with confidence level.
- Pattern/trap warnings if applicable.
- Attribution robustness note if data exists.
- Recommended next experiment with time estimate.
