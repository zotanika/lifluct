# Using LIFLUCT with AI Assistants

A practical guide for running AMM liquidity policy experiments through Claude Code, Gemini CLI, or Codex.

---

## 1. Getting Started

### Prerequisites

- Python 3.11 or later
- One of the supported AI assistants: Claude Code, Gemini CLI, or Codex

### Installation

**Claude Code (recommended)**

Two slash commands in any Claude Code session:

```
/plugin marketplace add zotanika/lifluct
/plugin install lifluct
```

That's it. Claude Code automatically clones the repo, sets up a Python environment, installs dependencies, starts the MCP server, and registers all commands and agents. No manual `pip install` or `git clone` needed.

**Gemini CLI / Codex**

```bash
pip install lifluct "mcp[cli]"
lifluct mcp install --gemini   # or --codex
```

### Verify the Installation

Once installed, ask your AI assistant:

```
Check if LIFLUCT is working.
```

The AI will call the `health` tool and report whether the server is running and can find the necessary directories.

---

## 2. Your First Experiment

This tutorial walks through a complete first-time session. You should be able to follow along and get results in under 5 minutes.

### Step 1: Ask the AI to Show Available Experiments

Start a conversation with your AI assistant and type:

```
What experiments can I run with LIFLUCT?
```

The AI calls `list_presets` and shows you the available templates. You will see something like this:

```
Here are the available LIFLUCT experiment presets:

Smoke Tests (quick, ~1 minute each):
  - smoke_dynamic: Quick dynamic fee test. Perfect oracle, low volatility.
  - smoke_static: Quick static CPMM baseline. The simplest AMM.

Stress Tests (~2 minutes each):
  - stress_oracle_lag: Dynamic fee under lagged oracle (3 steps).
  - stress_high_vol: Dynamic fee under high volatility (sigma=0.08).
  - stress_sabotage: Dynamic fee under sabotage adversary.

Comparison:
  - compare_dynamic_vs_static: Side-by-side dynamic fee vs static CPMM.

I'd recommend starting with smoke_dynamic to see how LIFLUCT works.
```

### Step 2: Run a Smoke Test

Type:

```
Run the smoke_dynamic preset.
```

The AI calls `run_preset("smoke_dynamic")` and waits for the simulation to finish. This takes about a minute. When complete, the AI reads the results and explains them:

```
Smoke test complete. Here's what happened:

LP vs HODL: +127.43 (quote asset units)
  The liquidity provider earned more than simply holding the assets.

Fee Revenue: 284.16
  Total fees collected from trades.

Attributed Loss: 156.73
  Value lost to informed (toxic) trading flow.

Revenue-to-Loss Ratio: 1.81
  Fees earned 1.81x the attributed loss. Above 1.0 is healthy.

Failure Modes: None detected.

This is a healthy result under gentle conditions. The dynamic fee
policy is collecting enough fees to more than offset adverse selection.

Recommended next step: Test with a lagged oracle (oracle_lag_steps=1,2,3)
to check robustness. Estimated time: ~6 minutes locally.
```

### Step 3: Understand the Numbers

Here is what each key metric means:

| Metric | What It Measures | Good Sign | Bad Sign |
|--------|-----------------|-----------|----------|
| `lp_minus_hodl_b` | Did the LP beat holding? | Positive | Negative |
| `total_lp_revenue_b` | Total fee income | Higher is better | Very low = no trading activity |
| `total_attributed_loss_b` | Cost of toxic flow | Lower is better | Exceeds revenue = net loss |
| `total_trader_cost_b` | Cost imposed on traders | Reasonable range | Very high = traders leave |
| `total_arbitrage_profit_b` | Arbitrageur earnings | Should exist | Dominates = LPs are prey |

The single most important number is `lp_minus_hodl_b`. If it is positive, the liquidity policy is earning its keep. If negative, the LP would have been better off doing nothing.

But a positive number alone is not enough. You also need to check that attributed loss is not dangerously close to revenue. If `total_attributed_loss_b > total_lp_revenue_b * 0.8`, the result is precarious, and small changes in conditions could flip it negative.

---

## 3. Testing Your Own Policy

### Describing Your Policy

You do not need to write YAML from scratch. Describe your policy in plain language:

```
Test a dynamic fee policy with f_min=0.005, mu=0.2, tau=0.003
under realistic conditions.
```

The AI uses `configure_experiment` to build a full configuration from your parameters, filling in sensible defaults for everything you did not specify.

### The Wizard Flow

When you ask to test a policy, the AI follows a structured process:

1. **Validate**: The AI calls `validate_config` to check your parameters for consistency issues. It will warn you about things like setting `oracle_mode=lagged` without specifying lag steps.

2. **Choose stress level**: The AI asks how harsh you want the test to be.
   - Gentle: perfect oracle, low volatility, standard adversary
   - Realistic: lagged oracle, moderate volatility, fee-aware adversary
   - Hostile: lagged oracle, high volatility, sabotage adversary

3. **Run your policy + a baseline**: The AI runs both your policy and a static CPMM baseline under identical conditions, so you have a fair comparison.

4. **Compare and interpret**: The AI calls `compare_runs` and explains which policy performed better and why.

### Example: Full Policy Test Conversation

```
You: Test my dynamic fee policy with f_min=0.005, mu=0.2, tau=0.003
     under realistic conditions.

AI:  I'll set up a realistic test for your dynamic fee policy.

     Configuration:
       - Dynamic fee: f_min=0.005, mu=0.2, tau=0.003
       - Oracle: lagged (2 steps)
       - Volatility: sigma=0.03
       - Adversary: fee-aware maximum extraction
       - Duration: 1000 steps

     Validation: OK, no issues found.

     Running your policy... done (52 seconds).
     Running static CPMM baseline... done (48 seconds).

     Comparison:

     Metric                   Your Policy    Static CPMM
     lp_minus_hodl_b          +89.21         -42.67
     total_lp_revenue_b       312.05         178.40
     total_attributed_loss_b  222.84         221.07
     total_trader_cost_b      15.82          8.93

     Verdict: Your dynamic fee policy outperforms the static CPMM by
     131.88 in LP outcome. Both face similar attributed loss, but your
     policy's higher fee revenue more than compensates.

     One caution: trader cost is 77% higher with your policy. In a
     competitive market, some flow could migrate to other venues.

     Recommended next: Run the 4-regime stress battery to confirm this
     holds under harsher conditions. Estimated time: ~8 minutes locally.
```

### Providing a Config File

If you already have a YAML config file, provide the path:

```
Test my policy at ./configs/my_policy.yaml
```

The AI reads the file, validates it, and runs the same wizard flow.

---

## 4. Stress Testing

### Asking for a Stress Test

```
Stress test my dynamic fee policy.
```

Or be more specific:

```
Run the 4-regime stress battery on my last experiment's config.
```

### The 4-Regime Battery

Stress testing runs your policy across four increasingly hostile environments:

| Regime | Oracle | Volatility | Adversary | What It Tests |
|--------|--------|-----------|-----------|---------------|
| Perfect Oracle | perfect | moderate | standard | Best-case baseline |
| Oracle Lag | lagged (3 steps) | moderate | fee-aware | Oracle fragility |
| High Volatility | perfect | high (sigma=0.08) | fee-aware | Fee responsiveness |
| Sabotage | lagged (2 steps) | moderate | sabotage | Maximum adversarial pressure |

### Parallel Execution

The AI dispatches four batch-runner agents in parallel, one for each regime. You will see progress updates as each finishes:

```
AI:  Running 4-regime stress battery...

     [1/4] Perfect Oracle: complete (48s) -- lp_minus_hodl_b = +142.31
     [2/4] Oracle Lag: complete (55s) -- lp_minus_hodl_b = +31.07
     [3/4] High Volatility: complete (61s) -- lp_minus_hodl_b = -18.92
     [4/4] Sabotage: complete (53s) -- lp_minus_hodl_b = -287.44
```

Total wall time is roughly the duration of the longest single run, not the sum of all four.

### Reading the Results

After all four regimes finish, the AI compares them and builds a narrative:

```
AI:  Stress Battery Results:

     Survived: 2/4 regimes (perfect oracle, oracle lag)
     Failed: 2/4 regimes (high volatility, sabotage)

     The policy handles oracle imprecision reasonably well (LP outcome
     still positive at lag=3). However, high volatility collapses fee
     revenue faster than loss grows, and the sabotage adversary
     extracts 287 units.

     Key finding: the policy's tau=0.003 threshold is too slow to
     react to sigma=0.08 volatility. Consider increasing mu or tau.

     Failure modes detected:
       - High Volatility: attributed_loss exceeds revenue (ratio 1.12)
       - Sabotage: dead-volume detected in final 20% of steps

     Recommended next: Run a best-fixed search to establish whether
     any static policy survives these same conditions better.
     Estimated: 8 runs, ~15 minutes locally.
```

### Understanding Estimated Local Time

When the AI says "estimated ~6 hours locally," it is reporting the actual compute time on your machine for a large experiment (like a 256-run regime family). This is a real estimate based on per-run timing, not a marketing pitch. The numbers simply report what the experiment requires.

---

## 5. Comparing and Analyzing Results

### Starting a Comparison

Use the slash command (Claude Code) or natural language (any platform):

```
/lifluct:compare
```

Or:

```
Compare my last three experiments.
```

The AI calls `list_runs` to find your recent experiments, then `compare_runs` to produce a side-by-side table.

### How the AI Builds Comparison Narratives

The AI follows a specific priority order when interpreting comparisons:

1. **Failure flags first**: If any run has failure modes, those are reported before metrics.
2. **LP vs HODL verdict**: Which policy wins on the primary metric?
3. **Attribution ratio**: Is the winner's advantage robust or fragile?
4. **Trader cost check**: Does the winner impose unreasonable costs on traders?
5. **Pattern matching**: Cross-references against known red flags and traps.

### Attribution Robustness

Attribution robustness measures whether your policy's advantage holds up under different ways of calculating loss. There are multiple attribution modes (observed spot, lagged, TWAP, future), and each produces different loss numbers for the same trades.

If your policy looks great under one attribution mode but terrible under another, that is a red flag. The AI checks this automatically:

```
AI:  Attribution robustness for run exp_a1b2c3_20260416:

     observed_spot: lp_minus_hodl_b = +89.21
     lagged_3:      lp_minus_hodl_b = +72.08
     twap_10:       lp_minus_hodl_b = +81.44
     future_5:      lp_minus_hodl_b = +93.56

     Robustness: STABLE. Ranking is consistent across all modes.
     The policy's advantage is not an artifact of a particular
     loss calculation method.
```

If the ranking flips between attribution modes, the AI warns you that the result is fragile and recommends further investigation.

### Pattern Detection

The AI checks results against three categories of known patterns:

**Healthy patterns**: Revenue comfortably exceeds attributed loss, no failure modes, LP outcome is positive across multiple regimes.

**Red flags**: Attributed loss exceeds 80% of revenue, dead-volume behavior in the pool, oracle fragility detected, or lysis triggered repeatedly.

**Traps**: Results that look good on the surface but hide structural problems. For example, high fee revenue driven by fees so aggressive that real traders would migrate to competing venues. The AI checks for these specifically and will call them out.

---

## 6. Understanding AI Recommendations

### How suggest_next_experiment Works

After every interpretation, the AI calls `suggest_next_experiment` with your completed run IDs. This tool analyzes what you have tested so far and recommends the most informative next step.

The response always includes:

- **recommendation**: What to run next, in plain language
- **rationale**: Why this experiment matters now
- **estimated_runs**: How many individual simulations
- **estimated_local_time_minutes**: Wall time on your machine
- **complexity**: single_run, sweep, or regime_family

### The Natural Progression

Experiments typically follow a logical escalation:

| Phase | What | Typical Runs | Time |
|-------|------|-------------|------|
| 1. Smoke test | Verify the setup works | 1 | ~1 min |
| 2. Comparison | Test against static baseline | 2 | ~2 min |
| 3. Stress battery | 4-regime robustness check | 4 | ~8 min |
| 4. Best-fixed search | Find the strongest fixed policy | 8-16 | ~15-30 min |
| 5. Regime family | Full multi-regime, multi-seed evaluation | 64-256 | ~2-6 hours |

The AI guides you through this progression. You do not need to memorize it.

### When the AI Reports Long Estimates

If the AI says "this regime family (256 runs) will take approximately 6 hours locally," that is a factual computation estimate. A few things to understand:

- Each run is independent. Total time scales linearly with run count.
- Your machine's CPU speed and available cores determine actual throughput.
- The AI reports these estimates so you can make informed decisions about when to start large experiments.
- For batch work that exceeds your patience or hardware budget, consider running overnight or on a more capable machine.

### Natural Scaling Limits

LIFLUCT runs locally on your machine. This is ideal for exploration and iterative policy development. At some point, you may encounter practical limits:

- A 256-run regime family takes hours on a laptop.
- Best-fixed search with fine resolution may need thousands of runs.
- Sharing results with teammates requires manually copying directories.
- Continuous evaluation across commits has no built-in automation.

The AI reports these constraints through the numbers. There is no upsell prompt -- just the estimated time and run count for whatever you ask it to do next.

---

## 7. Available Commands Reference

### Slash Commands (Claude Code)

| Command | Description |
|---------|-------------|
| `/lifluct:experiment` | Start guided experiment flow. Detects intent and enters the appropriate wizard. |
| `/lifluct:test` | Quick policy test. Pass a config file path or preset name. |
| `/lifluct:compare` | Compare experiment runs. Pass run IDs or let the AI list recent runs. |
| `/lifluct:analysis` | Deep analysis of results with pattern matching and attribution robustness. |

### MCP Tools (All Platforms)

These tools are available on all three platforms. On Gemini CLI and Codex, use natural language and the AI will call the appropriate tool.

**Discovery and Quick Start**

| Tool | Description |
|------|-------------|
| `health` | Check server status and directory configuration. |
| `list_presets` | Show available experiment templates by category. |
| `run_preset` | Run a named preset with optional seed override. |
| `explain_concept` | Look up a domain concept (amm, lp, toxic_flow, attribution, best_fixed, lysis, regime, oracle). |

**Custom Experiments**

| Tool | Description |
|------|-------------|
| `configure_experiment` | Build a config from high-level parameters with smart defaults. |
| `validate_config` | Check config for consistency issues before running. |
| `run_experiment` | Execute a simulation from a full config. |

**Results and Interpretation**

| Tool | Description |
|------|-------------|
| `read_results` | Read summary, failure modes, and diagnostics from a completed run. |
| `list_runs` | List tracked runs, optionally filtered by label. |
| `compare_runs` | Side-by-side comparison of 2+ runs. |
| `read_attribution_robustness` | Check whether results hold across different attribution modes. |

**Advisory**

| Tool | Description |
|------|-------------|
| `suggest_next_experiment` | Recommend the next experiment based on current results. |

---

## 8. Tips for Effective Use

### Be Specific About What You Want to Test

Instead of:

```
Test my policy.
```

Try:

```
Test a dynamic fee policy with f_min=0.005, mu=0.2, tau=0.003
under realistic oracle conditions (lag=2).
```

The more specific your parameters, the less the AI needs to guess, and the more useful the results will be.

### Provide Context About Your Goals

The AI interprets results differently depending on what you care about:

```
I'm optimizing for LP outcome and I'm willing to accept higher trader costs.
```

vs:

```
Trader cost needs to stay below 10 units. LP outcome is secondary.
```

### Trust the Failure Mode Warnings

When the AI reports failure modes, take them seriously. A result with `lp_minus_hodl_b = +50` but with oracle fragility detected is more dangerous than a result with `lp_minus_hodl_b = +30` and no failure flags. The positive number can vanish if oracle conditions degrade even slightly.

### Do Not Skip the Best-Fixed Baseline

This is the most important comparison in LIFLUCT. A best-fixed baseline is the strongest possible static policy, found by searching across parameter space. If your adaptive policy cannot beat this optimized static competitor, the adaptive mechanism may not be worth its complexity.

When the AI recommends a best-fixed search, run it. Many policies that look impressive against a naive static baseline collapse when measured against the best fixed alternative.

### Start Small, Then Escalate

Follow the natural progression: smoke test first, then comparison, then stress, then best-fixed, then regime family. Each step builds confidence (or reveals problems) that inform the next.

Jumping straight to a 256-run regime family without knowing whether your policy survives basic stress conditions wastes hours of compute time.

### Read the Attribution Robustness

If the AI offers attribution robustness data, read it. A policy whose advantage disappears under a different loss calculation method has a problem that will eventually surface in production. Stable results across attribution modes are the mark of a genuinely robust policy.

### Ask Questions

The AI has domain knowledge built in. If you do not understand a metric or concept, ask:

```
What does total_attributed_loss_b actually measure?
```

```
Why would a positive lp_minus_hodl_b still be a bad result?
```

```
Explain the difference between oracle modes.
```

The `explain_concept` tool provides detailed explanations with judgment criteria for all core LIFLUCT concepts.
