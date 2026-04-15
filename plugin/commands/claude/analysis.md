---
description: Analyze and compare LIFLUCT experiment results
allowed-tools: mcp__plugin_lifluct_lab__*, Read, Glob
---

You are analyzing LIFLUCT experiment results. Focus on interpretation and comparison.

## Process
1. Load relevant interpretation template from ai/interpretation/
2. Read results using MCP tools (read_results, compare_runs, read_attribution_robustness)
3. Apply pattern matching from ai/patterns/ (healthy.md, red_flags.md, traps.md)
4. Build narrative following the interpretation template's priority order
5. End with suggest_next_experiment recommendation including local time estimate
