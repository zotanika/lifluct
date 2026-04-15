# LIFLUCT AI Assistant Plugin

AI-assisted liquidity policy experimentation for the LIFLUCT framework.

## What This Does

Wraps LIFLUCT's simulation engine in an MCP server with a shared prompt library,
enabling AI assistants (Claude Code, Gemini CLI, Codex) to guide you through:

- **Policy setup** -- configure experiments from high-level intent or presets
- **Experiment execution** -- run simulations with proper baselines
- **Result interpretation** -- AI reads results and explains what they mean
- **Comparison analysis** -- cross-compare runs with pattern detection
- **Next step recommendations** -- AI suggests what to test next

## Quick Start

### Claude Code (recommended)

```bash
claude plugin install lifluct
```

Then in Claude Code:
```
/lifluct                         # Start guided experiment
/lifluct-test config.yaml        # Test a specific policy
/lifluct-compare                 # Compare experiment runs
```

### Gemini CLI

```bash
pip install lifluct
lifluct-mcp install --gemini
```

Then: `"Run a LIFLUCT smoke test"`

### Codex

```bash
pip install lifluct
lifluct-mcp install --codex
```

Then: `"Test my liquidity policy with LIFLUCT"`

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_presets` | Show available experiment templates |
| `run_preset` | Run a named preset |
| `explain_concept` | Explain an AMM/LIFLUCT concept |
| `configure_experiment` | Build config from high-level params |
| `validate_config` | Check config consistency |
| `run_experiment` | Execute a simulation |
| `read_results` | Read structured results |
| `list_runs` | List completed experiments |
| `compare_runs` | Compare runs side by side |
| `read_attribution_robustness` | Check attribution stability |
| `suggest_next_experiment` | AI-guided next step |

## Architecture

```
Plugin -> MCP Server (FastMCP) -> LIFLUCT Core (Python)
  |
Shared Prompt Library (knowledge, wizards, interpretation, patterns)
```

## Development

```bash
# Run tests
cd plugin/mcp/server && python -m pytest -v

# Run server directly
lifluct-mcp serve
```
