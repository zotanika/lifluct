# Interpretation: Single Run

How to read and present a single run's results. Follow this priority order strictly -- do not bury critical information beneath positive metrics.

## Priority Order

### 1. Check failure_modes first

If any failure modes are present, lead with them. Do not start with "the run completed successfully" if there are failures.

- Critical failures (`all_cells_inactive_shutdown`): "This run experienced complete system failure. [explanation]."
- High-severity failures (`dead_volume_equilibrium`, `lysis_cascade`, `oracle_fragility`): "This run has serious issues that undermine the results. [explanation]."
- Medium-severity failures (`inactive_cell_pathology`, `gene_collapse_to_bounds`, `no_convergence_oscillation`): "This run completed but shows structural problems. [explanation]."
- Low-severity failures (`monoculture_dominance`): Mention as a note, do not lead with it.

### 2. lp_minus_hodl_b verdict

The headline number. Report the sign and magnitude clearly.

- Positive: "The LP earned [amount] more than HODL."
- Negative: "The LP lost [amount] compared to HODL."
- Near zero: "The LP roughly broke even with HODL."

### 3. Attributed loss vs revenue ratio

Calculate: `total_attributed_loss_b / total_lp_revenue_b`

- < 0.5: "Revenue comfortably exceeds attributed losses. The margin is healthy."
- 0.5 -- 0.8: "Attributed losses consume a significant portion of revenue. The margin is thin."
- > 0.8: "Attributed losses nearly equal revenue. The positive result is precarious."
- > 1.0: "Attributed losses exceed revenue. The fee is not compensating for adverse selection."

### 4. Trader cost analysis

Check `total_trader_cost_b` relative to trade volume and LP revenue.

- If trader cost is reasonable: "Trader costs are moderate, suggesting the fee level is sustainable."
- If trader cost is very high: "Trader costs are very high. In a real market with alternative venues, this fee level would drive traders away, collapsing volume."

### 5. Arbitrage ratio

From `num_trades`, calculate the proportion of arbitrage trades.

- < 30% arb: "The pool is primarily serving genuine liquidity demand."
- 30-60% arb: "A significant share of trades are arbitrage. The fee should be higher to deter extractive flow."
- 60-90% arb: "Most trades are arbitrage. The pool is being used primarily for value extraction."
- > 90% arb: "The pool is overwhelmingly dominated by arbitrageurs."

## Narrative Templates

### Healthy Result

"This run produced a healthy result. The LP earned {lp_minus_hodl_b} above HODL, with fee revenue of {total_lp_revenue_b} against attributed losses of {total_attributed_loss_b} (ratio: {ratio}). Trader costs are moderate at {total_trader_cost_b}, and the trade mix is {noise_pct}% noise / {arb_pct}% arbitrage. No failure modes were detected.

The result suggests the fee policy is working as intended under these conditions ({oracle_mode} oracle, sigma={sigma})."

### Precarious Result

"This run is technically positive (lp_minus_hodl_b = {value}) but precarious. Attributed losses consume {ratio_pct}% of fee revenue, leaving a thin margin. A small change in conditions -- slightly more oracle lag, slightly higher volatility -- could flip this result negative.

Before trusting this result, check attribution robustness. If the positive verdict only holds under one attribution mode, it is likely an artifact."

### Failed Result

"This run failed. The LP lost {abs(lp_minus_hodl_b)} compared to HODL. Attributed losses of {total_attributed_loss_b} overwhelmed fee revenue of {total_lp_revenue_b}.

{If failure modes present: 'The following failure modes were detected: [list]. [Brief explanation of each.]'}

Root cause analysis: {based on which metrics are worst, identify the likely cause -- oracle lag, high vol, aggressive adversary, or fee misconfiguration}."

## Red Flags to Check

After constructing the narrative, cross-reference with:
- `patterns/red_flags.md` for danger patterns.
- `patterns/traps.md` for false-positive traps.

If any pattern matches, append: "Note: this result matches the [{pattern_name}] pattern, which means [{explanation}]."
