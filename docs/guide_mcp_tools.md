# LIFLUCT MCP Tool Reference Manual

This manual documents the 12 tools exposed by the LIFLUCT MCP server. It is
written for developers and power users who call tools directly -- without an AI
agent mediating. If you are building custom automation, integrating with
scripts, or simply prefer raw tool calls, this is the definitive reference.

All parameter names, types, defaults, and return structures are taken from
`plugin/mcp/server/server.py` and its supporting modules.

---

## Table of Contents

1. [Setup](#1-setup)
2. [Tool Reference](#2-tool-reference)
   - [health](#health)
   - [list_presets](#list_presets)
   - [run_preset](#run_preset)
   - [explain_concept](#explain_concept)
   - [configure_experiment](#configure_experiment)
   - [validate_config](#validate_config)
   - [run_experiment](#run_experiment)
   - [read_results](#read_results)
   - [list_runs](#list_runs)
   - [compare_runs](#compare_runs)
   - [read_attribution_robustness](#read_attribution_robustness)
   - [suggest_next_experiment](#suggest_next_experiment)
3. [Common Workflows](#3-common-workflows)
4. [Configuration Reference](#4-configuration-reference)
5. [Understanding Results](#5-understanding-results)
6. [Run Index](#6-run-index)
7. [Presets Reference](#7-presets-reference)

---

## 1. Setup

### Starting the MCP server

The server runs over stdio transport. Launch it directly:

```bash
lifluct mcp serve
```

Or invoke the server script with Python:

```bash
python plugin/mcp/server/server.py --mode stdio
```

### Configuration via `.mcp.json`

Place a `.mcp.json` file in your project root:

```json
{
  "mcpServers": {
    "lifluct": {
      "command": "/path/to/lifluct/.venv/bin/python3",
      "args": [
        "/path/to/lifluct/plugin/mcp/server/server.py",
        "--mode",
        "stdio"
      ],
      "env": {
        "PYTHONPATH": "/path/to/lifluct/plugin/mcp/server:/path/to/lifluct",
        "LIFLUCT_RUNS_DIR": "/path/to/lifluct/runs",
        "LIFLUCT_CONFIG_DIR": "/path/to/lifluct/lifluct/configs"
      }
    }
  }
}
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `LIFLUCT_RUNS_DIR` | `./runs` | Directory where experiment output directories are created. |
| `LIFLUCT_CONFIG_DIR` | `./lifluct/configs` | Directory containing config files (reported by `health`). |

Both variables are read at server startup. If not set, the defaults are
resolved relative to the working directory of the server process.

---

## 2. Tool Reference

### health

Check LIFLUCT server status.

**Parameters:** None.

**Returns:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | Always `true` if the server is running. |
| `runs_dir` | `string` | Resolved path to the runs directory. |
| `config_dir` | `string` | Resolved path to the config directory. |
| `runs_dir_exists` | `bool` | Whether the runs directory exists on disk. |
| `config_dir_exists` | `bool` | Whether the config directory exists on disk. |

**Example call:**

```json
{"tool": "health"}
```

**Example response:**

```json
{
  "ok": true,
  "runs_dir": "/home/user/lifluct/runs",
  "config_dir": "/home/user/lifluct/lifluct/configs",
  "runs_dir_exists": true,
  "config_dir_exists": true
}
```

**Notes:**
- Use this as a connectivity check before running experiments.
- If `runs_dir_exists` is `false`, experiment runs will create the directory
  automatically, but it may indicate a misconfigured `LIFLUCT_RUNS_DIR`.

---

### list_presets

List available experiment presets. Optionally filter by category.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `category` | `string` | `""` (all) | Filter by category. Valid values: `"smoke_test"`, `"stress_test"`, or `""` for all. |

**Returns:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | Success flag. |
| `presets` | `array` | List of preset objects. |

Each preset object:

| Field | Type | Description |
|---|---|---|
| `name` | `string` | Preset identifier used in `run_preset`. |
| `description` | `string` | Human-readable description. |
| `category` | `string` | `"smoke_test"` or `"stress_test"`. |
| `estimated_seconds` | `int` | Estimated wall-clock runtime. |

**Example call:**

```json
{"tool": "list_presets", "arguments": {"category": "smoke_test"}}
```

**Example response:**

```json
{
  "ok": true,
  "presets": [
    {
      "name": "smoke_dynamic",
      "description": "Quick dynamic fee test. ~1 min. Perfect oracle, low volatility.",
      "category": "smoke_test",
      "estimated_seconds": 60
    },
    {
      "name": "smoke_static",
      "description": "Quick static CPMM baseline. ~1 min. The simplest AMM.",
      "category": "smoke_test",
      "estimated_seconds": 60
    }
  ]
}
```

**Notes:**
- An empty `category` (the default) returns all presets across all categories.
- The returned list does not include the full config -- use `run_preset` to
  execute or inspect the presets reference table below for details.

---

### run_preset

Run a named preset experiment. Returns summary metrics and a `run_id`.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `preset_name` | `string` | *(required)* | Name of the preset to run. Must match a name from `list_presets`. |
| `seed` | `int` | `0` | Random seed override. When `0`, uses the preset's default seed (42). |
| `label` | `string` | `""` | Human-readable label for the run. Defaults to `"preset:<preset_name>"`. |

**Returns (success):**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true` on success. |
| `run_id` | `string` | Unique run identifier, formatted as `<preset_name>_<YYYYMMDD_HHMMSS>`. |
| `run_dir` | `string` | Absolute path to the output directory. |
| `summary` | `object` | Summary metrics dict (see [Understanding Results](#5-understanding-results)). |
| `failure_modes` | `array` | List of detected failure mode objects. |
| `validation_warnings` | `array` | List of config validation warning objects. |

**Returns (error):**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `false`. |
| `error` | `string` | Error message. |
| `available` | `array` | (If preset not found) List of valid preset names. |

**Example call:**

```json
{"tool": "run_preset", "arguments": {"preset_name": "smoke_dynamic", "seed": 123}}
```

**Example response:**

```json
{
  "ok": true,
  "run_id": "smoke_dynamic_20260416_142301",
  "run_dir": "/home/user/lifluct/runs/smoke_dynamic_20260416_142301",
  "summary": {
    "lp_minus_hodl_b": 42.7,
    "total_lp_revenue_b": 215.3,
    "total_attributed_loss_b": -172.6,
    "total_arbitrage_profit_b": 88.1,
    "total_fee_revenue_b": 215.3
  },
  "failure_modes": [],
  "validation_warnings": []
}
```

**Notes:**
- The run is executed synchronously. For presets with `estimated_seconds > 60`,
  the call may block for several minutes.
- The run is automatically registered in the SQLite run index (see
  [Run Index](#6-run-index)).
- If `seed` is `0`, it is not applied and the preset's default seed (42) is
  used.

---

### explain_concept

Look up a LIFLUCT domain concept. Returns a structured explanation with title,
short description, detailed explanation, and LIFLUCT-specific relevance.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `concept` | `string` | *(required)* | Concept key. Valid values: `amm`, `lp`, `toxic_flow`, `attribution`, `best_fixed`, `lysis`, `regime`, `oracle`. |

**Returns (success):**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true`. |
| `concept` | `string` | Normalized concept key. |
| `title` | `string` | Full title (e.g. "Automated Market Maker (AMM)"). |
| `short` | `string` | One-line summary. |
| `detail` | `string` | Multi-sentence explanation. |
| `relevance` | `string` | How this concept relates to LIFLUCT experiments. |

**Returns (error):**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `false`. |
| `error` | `string` | Error message. |
| `available_concepts` | `array` | Sorted list of valid concept keys. |

**Example call:**

```json
{"tool": "explain_concept", "arguments": {"concept": "toxic_flow"}}
```

**Example response:**

```json
{
  "ok": true,
  "concept": "toxic_flow",
  "title": "Toxic Flow (Adverse Selection)",
  "short": "Trades executed by informed arbitrageurs that systematically extract value from LPs.",
  "detail": "When an arbitrageur knows the true price has moved before the AMM updates, they trade at the stale price and pocket the difference. This flow is 'toxic' because it transfers value from LPs to arbitrageurs. The severity depends on oracle latency, volatility, and the fee level. Dynamic fees attempt to price this risk by raising fees when toxic flow is likely.",
  "relevance": "LIFLUCT models toxic flow via toxic_mode (cheapest_active, fee_aware_max_extraction, sabotage). The total_arbitrage_profit_b and total_attributed_loss_b metrics quantify how much value the adversary extracted. Failure modes flag when toxic flow overwhelms fee revenue."
}
```

**Notes:**
- The concept key is case-insensitive. Spaces and hyphens are normalized to
  underscores (e.g. `"toxic flow"` and `"toxic-flow"` both resolve to
  `"toxic_flow"`).

---

### configure_experiment

Build an experiment configuration dict with smart defaults. Returns a complete
JSON config ready for `validate_config` or `run_experiment`.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `baseline_type` | `string` | `"dynamic_fee_single"` | AMM policy type. See [Configuration Reference](#4-configuration-reference). |
| `oracle_mode` | `string` | `"perfect"` | Oracle type: `"perfect"` or `"lagged"`. |
| `oracle_lag_steps` | `int` | `0` | Number of steps the oracle lags behind. Only meaningful when `oracle_mode="lagged"`. |
| `sigma` | `float` | `0.02` | Per-step volatility of the price process. |
| `num_steps` | `int` | `1000` | Number of simulation time steps. |
| `seed` | `int` | `42` | Random seed. |
| `toxic_mode` | `string` | `"cheapest_active"` | Adversary strategy. See [Configuration Reference](#4-configuration-reference). |
| `use_dynamic_fee` | `bool` | `true` | Whether to enable dynamic fee adjustment. |
| `f_min` | `float` | `0.003` | Minimum fee (fee floor). |
| `mu` | `float` | `0.15` | Fee sensitivity to toxic flow signal. |
| `tau` | `float` | `0.002` | Fee decay rate (mean-reversion speed toward `f_min`). |
| `beta` | `float` | `0.0` | Fee asymmetry parameter. |
| `lysis_mode` | `string` | `"off"` | Cell death mode for turgor AMM: `"off"`, `"hard"`, or `"soft"`. |

**Returns:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true` on success. |
| `config` | `object` | Complete config dict including all base config fields and the specified overrides. |
| `config_hash` | `string` | 12-character SHA-256 hash of the config (for deduplication). |

The returned `config` object includes the following base fields (merged with
the parameters above):

| Field | Default | Description |
|---|---|---|
| `initial_reserve_a` | `1000.0` | Initial amount of asset A in the pool. |
| `initial_reserve_b` | `100000.0` | Initial amount of asset B in the pool. |
| `initial_price` | `100.0` | Starting price of A in terms of B. |
| `q_trade` | `0.35` | Trade arrival probability per step. |
| `max_trade_fraction_of_tvl` | `0.02` | Maximum trade size as fraction of TVL. |
| `arbitrage_threshold` | `0.001` | Minimum price discrepancy for arbitrage. |
| `tvl_target` | `200000.0` | Target total value locked. |
| `dt` | `1.0` | Time step size. |
| `oracle_observation_noise` | `0.01` | Noise added to oracle readings. |
| `num_cells` | `1` | Number of cells (for turgor mode). |
| `epoch_length` | `100` | Steps per evolutionary epoch. |
| `use_turgor` | `false` | Whether to enable turgor (multi-cell) mode. |
| `enable_evolution` | `false` | Whether to enable evolutionary parameter search. |
| `attribution_mode` | `"observed_spot"` | Primary attribution mode for loss measurement. |
| `user_routing_mode` | `"weighted_random"` | How user trades are routed across cells. |
| `s_base` | `1.0` | Base fitness scaling factor. |

**Example call:**

```json
{
  "tool": "configure_experiment",
  "arguments": {
    "baseline_type": "dynamic_fee_single",
    "sigma": 0.05,
    "oracle_mode": "lagged",
    "oracle_lag_steps": 3,
    "num_steps": 2000,
    "toxic_mode": "fee_aware_max_extraction"
  }
}
```

**Example response:**

```json
{
  "ok": true,
  "config": {
    "initial_reserve_a": 1000.0,
    "initial_reserve_b": 100000.0,
    "initial_price": 100.0,
    "q_trade": 0.35,
    "max_trade_fraction_of_tvl": 0.02,
    "arbitrage_threshold": 0.001,
    "tvl_target": 200000.0,
    "dt": 1.0,
    "oracle_observation_noise": 0.01,
    "num_cells": 1,
    "epoch_length": 100,
    "use_turgor": false,
    "enable_evolution": false,
    "attribution_mode": "observed_spot",
    "user_routing_mode": "weighted_random",
    "s_base": 1.0,
    "baseline_type": "dynamic_fee_single",
    "oracle_mode": "lagged",
    "oracle_lag_steps": 3,
    "sigma": 0.05,
    "num_steps": 2000,
    "seed": 42,
    "toxic_mode": "fee_aware_max_extraction",
    "use_dynamic_fee": true,
    "f_min": 0.003,
    "mu": 0.15,
    "tau": 0.002,
    "beta": 0.0,
    "lysis_mode": "off"
  },
  "config_hash": "a1b2c3d4e5f6"
}
```

**Notes:**
- This tool does not run any simulation. It only builds the config dict.
- The returned config is a complete, self-contained JSON object -- pass it
  directly to `validate_config` or `run_experiment`.
- To modify a single field from the defaults, specify only that field.
  All other fields inherit their defaults.

---

### validate_config

Validate an experiment config JSON string for consistency issues.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `config` | `string` | *(required)* | JSON-encoded config string (not an object -- must be a serialized string). |

**Returns:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true` if no issues found, `false` if issues exist or JSON is invalid. |
| `issues` | `array` | List of human-readable issue strings. Empty if config is valid. |
| `config` | `object` | The parsed config dict (echoed back). |

**Validation rules applied:**

1. **Required fields** -- `baseline_type`, `sigma`, `num_steps`, `seed` must be present.
2. **Oracle consistency** -- `oracle_mode="lagged"` with `oracle_lag_steps=0` is flagged (lag has no effect). `oracle_mode="perfect"` with `oracle_lag_steps>0` is flagged (lag is ignored).
3. **Fee consistency** -- `use_dynamic_fee=false` with `mu>0` is flagged (mu has no effect). `baseline_type="static_cpmm"` with `use_dynamic_fee=true` is flagged (conflict).
4. **Lysis consistency** -- `lysis_mode` set to anything other than `"off"` with `use_turgor=false` is flagged (lysis requires turgor mode).
5. **Range warnings** -- `sigma > 0.2` warns about unusually high volatility (typical range is 0.01--0.10). `num_steps > 50000` warns about long runtime.

**Example call:**

```json
{
  "tool": "validate_config",
  "arguments": {
    "config": "{\"baseline_type\": \"static_cpmm\", \"use_dynamic_fee\": true, \"sigma\": 0.02, \"num_steps\": 1000, \"seed\": 42}"
  }
}
```

**Example response:**

```json
{
  "ok": false,
  "issues": [
    "baseline_type='static_cpmm' with use_dynamic_fee=True \u2014 these conflict."
  ],
  "config": {
    "baseline_type": "static_cpmm",
    "use_dynamic_fee": true,
    "sigma": 0.02,
    "num_steps": 1000,
    "seed": 42
  }
}
```

**Notes:**
- The `config` parameter must be a JSON string, not a raw object. If you have a
  config dict from `configure_experiment`, serialize it with `JSON.stringify()`
  or `json.dumps()` before passing it.
- Validation does not guarantee a successful run. It catches common
  misconfiguration patterns but does not verify that every field is recognized
  by `RunConfig`.

---

### run_experiment

Run a simulation from a JSON config string. Returns summary, failure modes,
and a `run_id`.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `config` | `string` | *(required)* | JSON-encoded config string (the full config from `configure_experiment`). |
| `label` | `string` | `""` | Human-readable label. Defaults to `"custom:<config_hash>"`. |
| `retention_mode` | `string` | `"full_trace"` | Data retention level. `"full_trace"` saves all time-series data. |

**Returns (success):**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true`. |
| `run_id` | `string` | Unique ID, formatted as `exp_<config_hash>_<YYYYMMDD_HHMMSS>`. |
| `run_dir` | `string` | Absolute path to the output directory. |
| `summary` | `object` | Summary metrics dict. |
| `failure_modes` | `array` | List of failure mode objects. |
| `validation_warnings` | `array` | List of validation warning objects. |

**Returns (error):**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `false`. |
| `error` | `string` | Error message (invalid JSON, runtime failure, etc.). |

**Example call:**

```json
{
  "tool": "run_experiment",
  "arguments": {
    "config": "{\"baseline_type\": \"dynamic_fee_single\", \"sigma\": 0.03, \"num_steps\": 1000, \"seed\": 42, \"oracle_mode\": \"perfect\", \"oracle_lag_steps\": 0, \"toxic_mode\": \"cheapest_active\", \"use_dynamic_fee\": true, \"f_min\": 0.003, \"mu\": 0.15, \"tau\": 0.002, \"beta\": 0.0, \"lysis_mode\": \"off\", \"initial_reserve_a\": 1000.0, \"initial_reserve_b\": 100000.0, \"initial_price\": 100.0, \"q_trade\": 0.35, \"max_trade_fraction_of_tvl\": 0.02, \"arbitrage_threshold\": 0.001, \"tvl_target\": 200000.0, \"dt\": 1.0, \"oracle_observation_noise\": 0.01, \"num_cells\": 1, \"epoch_length\": 100, \"use_turgor\": false, \"enable_evolution\": false, \"attribution_mode\": \"observed_spot\", \"user_routing_mode\": \"weighted_random\", \"s_base\": 1.0}",
    "label": "custom_sigma_0.03"
  }
}
```

**Example response:**

```json
{
  "ok": true,
  "run_id": "exp_a1b2c3d4e5f6_20260416_143022",
  "run_dir": "/home/user/lifluct/runs/exp_a1b2c3d4e5f6_20260416_143022",
  "summary": {
    "lp_minus_hodl_b": 18.4,
    "total_lp_revenue_b": 310.2,
    "total_attributed_loss_b": -291.8,
    "total_arbitrage_profit_b": 155.0,
    "total_fee_revenue_b": 310.2
  },
  "failure_modes": [],
  "validation_warnings": []
}
```

**Notes:**
- Like `run_preset`, this executes synchronously. Long runs (many steps) will
  block.
- The `config` parameter must be a JSON string. Use the output of
  `configure_experiment` and serialize the `config` field.
- The run is automatically registered in the run index.
- Use `retention_mode="full_trace"` (the default) to enable attribution
  robustness analysis via `read_attribution_robustness`.

---

### read_results

Read summary, failure modes, and diagnostics from a completed run. Look up by
`run_id` (from the index) or `run_dir` (direct path).

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `run_id` | `string` | `""` | Run identifier from the index. |
| `run_dir` | `string` | `""` | Direct path to the run output directory. |

At least one of `run_id` or `run_dir` must be provided. If both are given,
`run_dir` takes precedence.

**Returns (success):**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true`. |
| `run_dir` | `string` | Resolved path to the run directory. |
| `summary` | `object\|null` | Contents of `summary.json`, or `null` if not found. |
| `failure_modes` | `object\|null` | Contents of `failure_modes.json`, or `null` if not found. |
| `validation_warnings` | `object\|null` | Contents of `validation_warnings.json`, or `null` if not found. |
| `diagnostics` | `object\|null` | Contents of `diagnostics.json`, or `null` if not found. |
| `available_artifacts` | `array` | Sorted list of all files in the run directory (relative paths). |

**Example call:**

```json
{"tool": "read_results", "arguments": {"run_id": "smoke_dynamic_20260416_142301"}}
```

**Example response:**

```json
{
  "ok": true,
  "run_dir": "/home/user/lifluct/runs/smoke_dynamic_20260416_142301",
  "summary": {
    "lp_minus_hodl_b": 42.7,
    "total_lp_revenue_b": 215.3,
    "total_attributed_loss_b": -172.6
  },
  "failure_modes": [],
  "validation_warnings": [],
  "diagnostics": null,
  "available_artifacts": [
    "attribution_mode_comparison.json",
    "attribution_ranking_stability.json",
    "config.json",
    "diagnostics.json",
    "failure_modes.json",
    "summary.json",
    "trace.parquet",
    "validation_warnings.json"
  ]
}
```

**Notes:**
- When using `run_id`, the tool resolves the path via the SQLite run index. If
  the run was not registered (e.g., created outside of MCP tools), use
  `run_dir` instead.
- The `available_artifacts` list lets you discover what files exist, including
  trace data (e.g. `trace.parquet`) that is not loaded by this tool.
- Fields are `null` when the corresponding JSON file does not exist in the run
  directory.

---

### list_runs

List tracked experiment runs from the SQLite run index.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `filter_label` | `string` | `""` | Filter runs whose label contains this substring (case-sensitive SQL LIKE). |
| `limit` | `int` | `50` | Maximum number of runs to return. |

**Returns:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true`. |
| `runs` | `array` | List of run records, ordered by `created_at` descending (most recent first). |
| `count` | `int` | Number of runs returned. |

Each run record:

| Field | Type | Description |
|---|---|---|
| `run_id` | `string` | Unique run identifier. |
| `run_dir` | `string` | Absolute path to the output directory. |
| `label` | `string` | Human-readable label. |
| `config_hash` | `string` | 12-character SHA-256 hash of the config. |
| `config_summary` | `object` | Subset of config fields: `baseline_type`, `oracle_mode`, `sigma`, `seed`. |
| `summary_metrics` | `object` | Summary metrics from the run (same as `summary` in run results). |
| `created_at` | `string` | ISO 8601 timestamp (UTC). |

**Example call:**

```json
{"tool": "list_runs", "arguments": {"filter_label": "preset:", "limit": 10}}
```

**Example response:**

```json
{
  "ok": true,
  "runs": [
    {
      "run_id": "smoke_dynamic_20260416_142301",
      "run_dir": "/home/user/lifluct/runs/smoke_dynamic_20260416_142301",
      "label": "preset:smoke_dynamic",
      "config_hash": "f3a1b2c4d5e6",
      "config_summary": {
        "baseline_type": "dynamic_fee_single",
        "oracle_mode": "perfect",
        "sigma": 0.02,
        "seed": 42
      },
      "summary_metrics": {
        "lp_minus_hodl_b": 42.7
      },
      "created_at": "2026-04-16T14:23:01.000000+00:00"
    }
  ],
  "count": 1
}
```

**Notes:**
- The filter uses SQL `LIKE '%<filter_label>%'` matching, so `"preset:"` matches
  all labels containing the substring `"preset:"`.
- Only runs registered via MCP tools appear in the index. Runs created by
  direct CLI invocation are not indexed unless manually registered.
- The SQLite index has a hard limit cap of 100 rows in the underlying query,
  but the `limit` parameter defaults to 50.

---

### compare_runs

Compare multiple runs by their summary metrics. Determines a winner based on
`lp_minus_hodl_b`.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `run_ids` | `string` | `""` | Comma-separated run IDs (at least 2 required). |

**Returns (success):**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true`. |
| `runs` | `array` | List of run comparison objects. |
| `winner` | `object\|null` | The run with the highest `lp_minus_hodl_b`, or `null` if no metrics available. |

Each run comparison object:

| Field | Type | Description |
|---|---|---|
| `run_id` | `string` | Run identifier. |
| `label` | `string` | Run label. |
| `config_summary` | `object` | Config subset (`baseline_type`, `oracle_mode`, `sigma`, `seed`). |
| `summary_metrics` | `object` | Full summary metrics. |

Winner object:

| Field | Type | Description |
|---|---|---|
| `run_id` | `string` | Winning run's ID. |
| `lp_minus_hodl_b` | `float` | The winning run's LP-minus-HODL value. |

**Example call:**

```json
{
  "tool": "compare_runs",
  "arguments": {
    "run_ids": "smoke_dynamic_20260416_142301,smoke_static_20260416_142500"
  }
}
```

**Example response:**

```json
{
  "ok": true,
  "runs": [
    {
      "run_id": "smoke_dynamic_20260416_142301",
      "label": "preset:smoke_dynamic",
      "config_summary": {"baseline_type": "dynamic_fee_single", "oracle_mode": "perfect", "sigma": 0.02, "seed": 42},
      "summary_metrics": {"lp_minus_hodl_b": 42.7, "total_lp_revenue_b": 215.3}
    },
    {
      "run_id": "smoke_static_20260416_142500",
      "label": "preset:smoke_static",
      "config_summary": {"baseline_type": "static_cpmm", "oracle_mode": "perfect", "sigma": 0.02, "seed": 42},
      "summary_metrics": {"lp_minus_hodl_b": -15.2, "total_lp_revenue_b": 120.1}
    }
  ],
  "winner": {
    "run_id": "smoke_dynamic_20260416_142301",
    "lp_minus_hodl_b": 42.7
  }
}
```

**Notes:**
- Requires at least 2 run IDs. Returns an error if fewer than 2 are provided.
- All run IDs must exist in the index. If any ID is not found, the entire call
  fails with an error identifying the missing ID.
- The winner is determined solely by the `lp_minus_hodl_b` metric (higher is
  better). This is the LP portfolio value minus what holding the initial assets
  would have yielded.
- `winner` is `null` if none of the runs have a `lp_minus_hodl_b` metric.

---

### read_attribution_robustness

Read attribution mode comparison and ranking stability data from a completed
run. This data shows whether LP return conclusions are robust across different
loss attribution methods.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `run_id` | `string` | *(required)* | Run identifier from the index. |

**Returns (success):**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true`. |
| `run_id` | `string` | The requested run ID. |
| `attribution_mode_comparison` | `object\|null` | Contents of `attribution_mode_comparison.json`, or `null`. |
| `attribution_ranking_stability` | `object\|null` | Contents of `attribution_ranking_stability.json`, or `null`. |
| `note` | `string` | (Only when both are `null`) Explanation that robustness data is not available. |

**Example call:**

```json
{"tool": "read_attribution_robustness", "arguments": {"run_id": "smoke_dynamic_20260416_142301"}}
```

**Example response (data available):**

```json
{
  "ok": true,
  "run_id": "smoke_dynamic_20260416_142301",
  "attribution_mode_comparison": {
    "modes": ["observed_spot", "twap", "delayed"],
    "lp_minus_hodl_b": {"observed_spot": 42.7, "twap": 38.1, "delayed": 44.3}
  },
  "attribution_ranking_stability": {
    "rankings_consistent": true,
    "mode_rank_changes": 0
  }
}
```

**Example response (no data):**

```json
{
  "ok": true,
  "run_id": "smoke_dynamic_20260416_142301",
  "attribution_mode_comparison": null,
  "attribution_ranking_stability": null,
  "note": "No attribution robustness data found. This is generated only when full_trace retention is used and the run has sufficient data."
}
```

**Notes:**
- Attribution robustness data is only generated when `retention_mode="full_trace"`
  was used during the run and the simulation produced sufficient data.
- If both files are missing, the response includes a `note` field explaining
  why.
- This tool reads from `attribution_mode_comparison.json` and
  `attribution_ranking_stability.json` in the run directory.

---

### suggest_next_experiment

Analyze completed runs and recommend what experiment to run next. The advisor
uses a rule-based engine that considers run count, failure modes, oracle
configuration, and metric trends.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `run_ids` | `string` | `""` | Comma-separated run IDs. Empty string triggers no-run advice. |

**Returns:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true`. |
| `recommendation` | `string` | What to do next. |
| `rationale` | `string` | Why this is the recommended next step. |
| `estimated_runs` | `int` | How many runs the recommendation involves. |
| `estimated_local_time_minutes` | `int` | Estimated wall-clock time. |
| `complexity` | `string` | `"single_run"`, `"sweep"`, or `"regime_family"`. |

**Advisor logic by number of runs:**

| Runs | Condition | Recommendation |
|---|---|---|
| 0 | -- | Run `smoke_dynamic` preset to establish a baseline. |
| 1 | Has failure modes | Investigate failures; run 3--5 targeted variants. |
| 1 | Perfect oracle, no failures | Test with lagged oracle (`oracle_lag_steps=3`). |
| 1 | No static baseline | Run `smoke_static` for A/B comparison. |
| 2--9 | All `lp_minus_hodl_b >= 0`, no failures | Run best-fixed fee search (8 fee levels). |
| 2--9 | Mixed results or failures | Run 4-regime stress battery. |
| 10+ | -- | Full regime family sweep (256 configurations). |

**Example call (no prior runs):**

```json
{"tool": "suggest_next_experiment", "arguments": {"run_ids": ""}}
```

**Example response:**

```json
{
  "ok": true,
  "recommendation": "Run the smoke_dynamic preset to establish a baseline.",
  "rationale": "No experiments have been run yet. A single smoke test with perfect oracle and low volatility confirms that the framework is working and gives you a baseline LP return to compare against.",
  "estimated_runs": 1,
  "estimated_local_time_minutes": 1,
  "complexity": "single_run"
}
```

**Example call (with prior runs):**

```json
{
  "tool": "suggest_next_experiment",
  "arguments": {
    "run_ids": "smoke_dynamic_20260416_142301,smoke_static_20260416_142500"
  }
}
```

**Notes:**
- The advisor loads `failure_modes.json` from disk for each run to inform
  its decision. If the file is missing, it assumes no failure modes.
- When `run_ids` is empty, the advisor returns the cold-start recommendation
  without consulting the index.
- The advisor does not execute any experiments -- it only returns a
  recommendation. You must call `run_preset` or `run_experiment` separately.

---

## 3. Common Workflows

### Workflow A: Quick Smoke Test

Confirm the server is working and get a baseline result.

```
Step 1: health()
Step 2: list_presets()
Step 3: run_preset(preset_name="smoke_dynamic")
Step 4: read_results(run_id=<run_id from step 3>)
```

**Concrete example:**

```json
// Step 1
{"tool": "health"}
// -> {"ok": true, "runs_dir": "...", "runs_dir_exists": true, ...}

// Step 2
{"tool": "list_presets"}
// -> {"ok": true, "presets": [{"name": "smoke_dynamic", ...}, ...]}

// Step 3
{"tool": "run_preset", "arguments": {"preset_name": "smoke_dynamic"}}
// -> {"ok": true, "run_id": "smoke_dynamic_20260416_142301", "summary": {...}, ...}

// Step 4
{"tool": "read_results", "arguments": {"run_id": "smoke_dynamic_20260416_142301"}}
// -> {"ok": true, "summary": {...}, "available_artifacts": [...], ...}
```

### Workflow B: Custom Policy Evaluation

Build a config, validate it, run the experiment, and get advisor guidance.

```
Step 1: configure_experiment(baseline_type="dynamic_fee_single", sigma=0.03, oracle_mode="lagged", oracle_lag_steps=2)
Step 2: validate_config(config=JSON.stringify(<config from step 1>))
Step 3: run_experiment(config=JSON.stringify(<config from step 1>), label="lagged_oracle_test")
Step 4: read_results(run_id=<run_id from step 3>)
Step 5: suggest_next_experiment(run_ids=<run_id from step 3>)
```

**Key detail:** The `config` field from `configure_experiment` is a JSON object.
Both `validate_config` and `run_experiment` expect a JSON *string*. You must
serialize the config object before passing it.

### Workflow C: Comparative Analysis

Run two policies side-by-side and compare results.

```
Step 1: configure_experiment(baseline_type="dynamic_fee_single", sigma=0.03)
Step 2: configure_experiment(baseline_type="static_cpmm", sigma=0.03, use_dynamic_fee=false, mu=0.0, tau=0.0)
Step 3: run_experiment(config=<config from step 1>, label="dynamic")
Step 4: run_experiment(config=<config from step 2>, label="static")
Step 5: compare_runs(run_ids="<run_id from step 3>,<run_id from step 4>")
Step 6: read_attribution_robustness(run_id=<run_id from step 3>)
```

**What to look for:**
- The `winner` in the `compare_runs` response tells you which policy had
  higher `lp_minus_hodl_b`.
- Attribution robustness (step 6) tells you whether the winning conclusion
  holds across different measurement methods.

### Workflow D: Progressive Evaluation

A full evaluation sequence from first contact to comprehensive analysis.

```
Phase 1 -- Smoke test:
  run_preset(preset_name="smoke_dynamic")
  run_preset(preset_name="smoke_static")
  compare_runs(run_ids="<dynamic_id>,<static_id>")

Phase 2 -- Stress testing:
  run_preset(preset_name="stress_oracle_lag")
  run_preset(preset_name="stress_high_vol")
  run_preset(preset_name="stress_sabotage")
  compare_runs(run_ids="<all_stress_ids>")

Phase 3 -- Advisor-guided exploration:
  suggest_next_experiment(run_ids="<all_ids>")
  // Follow recommendations (best-fixed search, regime family, etc.)

Phase 4 -- Robustness check:
  read_attribution_robustness(run_id=<best_run>)
```

---

## 4. Configuration Reference

### `baseline_type`

Controls the AMM's fee policy architecture.

| Value | Description |
|---|---|
| `"dynamic_fee_single"` | Single-cell AMM with dynamic fee adjustment. The fee responds to detected toxic flow. This is the primary policy under evaluation. |
| `"static_cpmm"` | Constant-product market maker with a fixed fee. No dynamic adjustment. Used as a baseline for comparison. |

### `oracle_mode`

Controls how the AMM observes the true market price.

| Value | Description |
|---|---|
| `"perfect"` | The AMM sees the true price instantly, with no delay. Best-case scenario for LP protection. |
| `"lagged"` | The oracle delivers the price with a delay of `oracle_lag_steps` time steps. Creates a window where arbitrageurs can profit from stale prices. |

### `toxic_mode`

Controls the adversary's trading strategy.

| Value | Description |
|---|---|
| `"cheapest_active"` | Adversary trades when the arbitrage opportunity exceeds the fee. Moderate pressure. |
| `"fee_aware_max_extraction"` | Adversary optimizes trade size to maximize extraction given the current fee level. Higher pressure than `cheapest_active`. |
| `"sabotage"` | Adversary aims to maximize LP losses regardless of its own profit. Maximum adversarial pressure. |

### Fee parameters

These parameters control the dynamic fee schedule (only effective when
`use_dynamic_fee=true`).

| Parameter | Type | Default | Effect |
|---|---|---|---|
| `f_min` | `float` | `0.003` | Fee floor. The fee never drops below this value. Higher values protect LPs but reduce trade volume. |
| `mu` | `float` | `0.15` | Fee sensitivity. Controls how aggressively the fee rises in response to detected toxic flow. Higher `mu` = faster fee escalation. |
| `tau` | `float` | `0.002` | Fee decay rate. Controls how quickly the fee reverts toward `f_min` after toxic flow subsides. Higher `tau` = faster reversion. |
| `beta` | `float` | `0.0` | Fee asymmetry. When non-zero, the fee responds differently to buys vs. sells. `0.0` means symmetric fee treatment. |

### `lysis_mode`

Controls cell death in turgor (multi-cell) mode. Only meaningful when
`use_turgor=true`.

| Value | Description |
|---|---|
| `"off"` | No cell removal. All cells persist for the entire simulation. |
| `"hard"` | Immediate removal of cells whose fitness falls below the lysis threshold. |
| `"soft"` | Gradual fitness penalty for underperforming cells, leading to eventual removal. |

### Other notable parameters

| Parameter | Default | Description |
|---|---|---|
| `sigma` | `0.02` | Per-step price volatility. Typical range: 0.01--0.10. Values above 0.20 are flagged by validation. |
| `num_steps` | `1000` | Simulation length. 400 for smoke tests, 1000 for standard runs, up to 50000 for long-horizon analysis. |
| `seed` | `42` | Random seed for reproducibility. Same seed + same config = identical results. |
| `oracle_lag_steps` | `0` | Number of steps the oracle lags behind. Only meaningful with `oracle_mode="lagged"`. |
| `oracle_observation_noise` | `0.01` | Gaussian noise added to oracle readings. |
| `q_trade` | `0.35` | Probability of a user trade arriving at each time step. |
| `attribution_mode` | `"observed_spot"` | Primary method for measuring per-trade LP impact. |
| `num_cells` | `1` | Number of cells in turgor mode. |
| `use_turgor` | `false` | Enable multi-cell turgor mode. |
| `enable_evolution` | `false` | Enable evolutionary parameter search across cells. |

---

## 5. Understanding Results

### Summary metrics

The `summary` object returned by `run_preset`, `run_experiment`, and
`read_results` contains the core performance metrics.

| Metric | Description |
|---|---|
| `lp_minus_hodl_b` | **Primary metric.** LP portfolio value minus HODL value, denominated in asset B. Positive means the fee policy compensated for divergence loss. Negative means LPs would have been better off holding. |
| `total_lp_revenue_b` | Total fee revenue earned by LPs, in asset B. |
| `total_attributed_loss_b` | Total attributed loss from adverse selection, in asset B. Typically negative. |
| `total_arbitrage_profit_b` | Total profit extracted by arbitrageurs, in asset B. |
| `total_fee_revenue_b` | Total fees collected by the AMM, in asset B. |

### Failure modes

The `failure_modes` array contains objects describing detected problems.

| Field | Description |
|---|---|
| `mode` | Identifier for the failure type (e.g., fee-related, oracle-related). |
| `severity` | Severity level: `"low"`, `"medium"`, `"high"`, or `"critical"`. |
| `evidence` | Supporting data (parameter values, metric thresholds) that triggered the detection. |

Severity interpretation:

| Level | Meaning |
|---|---|
| `low` | Minor concern. The policy is working but with suboptimal parameters. |
| `medium` | Noticeable problem. LP returns are degraded but not catastrophic. |
| `high` | Serious issue. The policy is failing to protect LPs under these conditions. |
| `critical` | Complete failure. LPs are losing significantly more than HODL. Immediate investigation needed. |

### Validation warnings

The `validation_warnings` array contains objects flagging config issues
detected during the run (distinct from `validate_config` pre-run checks).

### Attribution robustness data

Available via `read_attribution_robustness`. Two files are checked:

- **`attribution_mode_comparison.json`** -- Shows the same run's results
  computed under different attribution modes. If `lp_minus_hodl_b` varies
  substantially across modes, the conclusion is fragile.
- **`attribution_ranking_stability.json`** -- Shows whether the relative
  ranking of policies (which is better) changes across modes. Stable rankings
  mean the conclusion is robust even if absolute values shift.

---

## 6. Run Index

### Overview

LIFLUCT uses a lightweight SQLite database to track experiment runs across
sessions. Every run created via `run_preset` or `run_experiment` is
automatically registered.

### Location

```
~/.lifluct/runs.db
```

The directory `~/.lifluct/` is created automatically on first use.

### Schema

The `runs` table has the following columns:

| Column | Type | Description |
|---|---|---|
| `run_id` | `TEXT` (PK) | Unique run identifier. |
| `run_dir` | `TEXT` | Absolute path to the run's output directory. |
| `label` | `TEXT` | Human-readable label (e.g. `"preset:smoke_dynamic"`, `"custom:a1b2c3"`). |
| `config_hash` | `TEXT` | 12-character SHA-256 hash of the serialized config. |
| `config_summary` | `TEXT` | JSON string containing a subset of config fields: `baseline_type`, `oracle_mode`, `sigma`, `seed`. |
| `summary_metrics` | `TEXT` | JSON string containing the run's summary metrics. |
| `created_at` | `TEXT` | ISO 8601 timestamp (UTC) of when the run was registered. |

### How `list_runs` filtering works

- When `filter_label` is provided, the query uses SQL `LIKE '%<filter_label>%'`
  on the `label` column.
- Results are ordered by `created_at DESC` (most recent first).
- The `limit` parameter caps the number of rows returned (default 50, hard max
  100 in the underlying query).
- `config_summary` and `summary_metrics` are automatically deserialized from
  JSON strings to objects in the response.

### Direct access

You can query the database directly for advanced use cases:

```bash
sqlite3 ~/.lifluct/runs.db "SELECT run_id, label, config_hash FROM runs ORDER BY created_at DESC LIMIT 10;"
```

---

## 7. Presets Reference

All presets share a common base configuration:

| Base parameter | Value |
|---|---|
| `seed` | `42` |
| `initial_reserve_a` | `1000.0` |
| `initial_reserve_b` | `100000.0` |
| `initial_price` | `100.0` |
| `q_trade` | `0.35` |
| `max_trade_fraction_of_tvl` | `0.02` |
| `arbitrage_threshold` | `0.001` |
| `tvl_target` | `200000.0` |
| `dt` | `1.0` |
| `oracle_observation_noise` | `0.01` |
| `num_cells` | `1` |
| `epoch_length` | `100` |
| `use_turgor` | `false` |
| `enable_evolution` | `false` |
| `lysis_mode` | `"off"` |
| `attribution_mode` | `"observed_spot"` |
| `user_routing_mode` | `"weighted_random"` |
| `s_base` | `1.0` |
| `beta` | `0.0` |

### Preset table

| Name | Category | Est. Time | `num_steps` | `sigma` | `baseline_type` | `use_dynamic_fee` | `oracle_mode` | `oracle_lag_steps` | `f_min` | `mu` | `tau` | `toxic_mode` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `smoke_dynamic` | smoke_test | 60s | 400 | 0.02 | `dynamic_fee_single` | `true` | `perfect` | 0 | 0.003 | 0.15 | 0.002 | `cheapest_active` |
| `smoke_static` | smoke_test | 60s | 400 | 0.02 | `static_cpmm` | `false` | `perfect` | 0 | 0.003 | 0.0 | 0.0 | `cheapest_active` |
| `stress_oracle_lag` | stress_test | 120s | 1000 | 0.03 | `dynamic_fee_single` | `true` | `lagged` | 3 | 0.003 | 0.15 | 0.002 | `fee_aware_max_extraction` |
| `stress_high_vol` | stress_test | 120s | 1000 | 0.08 | `dynamic_fee_single` | `true` | `perfect` | 0 | 0.003 | 0.15 | 0.002 | `fee_aware_max_extraction` |
| `stress_sabotage` | stress_test | 120s | 1000 | 0.03 | `dynamic_fee_single` | `true` | `lagged` | 2 | 0.003 | 0.15 | 0.002 | `sabotage` |

### Preset descriptions

- **`smoke_dynamic`** -- Quick dynamic fee test. Perfect oracle, low volatility. Use as a first sanity check and baseline.
- **`smoke_static`** -- Quick static CPMM baseline. The simplest AMM. Compare against `smoke_dynamic` to see if dynamic fees add value.
- **`stress_oracle_lag`** -- Dynamic fee under a lagged oracle (3 steps). Tests whether the fee policy degrades when the oracle is delayed.
- **`stress_high_vol`** -- Dynamic fee under high volatility (sigma=0.08). Tests whether the fee responds fast enough to large price swings.
- **`stress_sabotage`** -- Dynamic fee under a sabotage adversary with lagged oracle. Maximum adversarial pressure. If the policy survives this, it is robust.
