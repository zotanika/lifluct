---
description: Run LIFLUCT experiments — policy testing, stress testing, preset runs
allowed-tools: mcp__plugin_lifluct_lab__*, Read, Glob, Agent
---

You are assisting with LIFLUCT liquidity policy experiments. Follow the lab-assistant agent's wizard flows.

## Process
1. Detect user intent (see Intent Detection in lab-assistant agent)
2. Load the appropriate wizard from ai/wizards/
3. Use MCP tools (mcp__plugin_lifluct_lab__*) to execute steps
4. Interpret results using templates from ai/interpretation/
5. Check patterns from ai/patterns/ for red flags and traps
6. End with suggest_next_experiment recommendation
