"""LIFLUCT MCP Server — experiment engine for liquidity policy evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from advisor import suggest_next
from knowledge import explain_concept as _explain_concept, list_concepts
from presets import get_preset, list_presets as _list_presets
from run_index import RunIndex

# ---------------------------------------------------------------------------
# Base config for configure_experiment — all required RunConfig fields
# ---------------------------------------------------------------------------
_BASE_CONFIG: dict[str, Any] = {
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
    "use_turgor": False,
    "enable_evolution": False,
    "attribution_mode": "observed_spot",
    "user_routing_mode": "weighted_random",
    "s_base": 1.0,
}


def _config_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:12]


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_server(
    *,
    runs_dir: str | None = None,
    config_dir: str | None = None,
) -> FastMCP:
    runs_dir = runs_dir or os.environ.get("LIFLUCT_RUNS_DIR", "./runs")
    config_dir = config_dir or os.environ.get("LIFLUCT_CONFIG_DIR", "./lifluct/configs")

    mcp = FastMCP(
        name="lifluct",
    )

    index = RunIndex()

    # -----------------------------------------------------------------------
    # Health
    # -----------------------------------------------------------------------
    @mcp.tool(name="health", description="Check LIFLUCT server status")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "runs_dir": str(runs_dir),
            "config_dir": str(config_dir),
            "runs_dir_exists": Path(runs_dir).is_dir(),
            "config_dir_exists": Path(config_dir).is_dir(),
        }

    # ===================================================================
    # Tier 1: Discovery & quick start
    # ===================================================================

    @mcp.tool(
        name="list_presets",
        description="List available experiment presets. Optionally filter by category (smoke_test, stress_test).",
    )
    async def tool_list_presets(category: str = "") -> dict[str, Any]:
        try:
            results = _list_presets(category=category or None)
            return {"ok": True, "presets": results}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @mcp.tool(
        name="run_preset",
        description="Run a named preset experiment. Returns summary metrics and run_id.",
    )
    async def tool_run_preset(preset_name: str, seed: int = 0, label: str = "") -> dict[str, Any]:
        try:
            from lifluct.cli.run_simulation import execute_and_write_run
            from lifluct.types import RunConfig

            preset = get_preset(preset_name)
            if preset is None:
                available = [p["name"] for p in _list_presets()]
                return {"ok": False, "error": f"Unknown preset: {preset_name!r}", "available": available}

            config_dict = preset["config"]
            if seed != 0:
                config_dict["seed"] = seed

            rc = RunConfig.from_mapping(config_dict)

            ts = _timestamp()
            run_id = f"{preset_name}_{ts}"
            run_label = label or f"preset:{preset_name}"
            output_dir = Path(runs_dir) / run_id
            output_dir.mkdir(parents=True, exist_ok=True)

            result = execute_and_write_run(
                config=rc, output_dir=output_dir, retention_mode="full_trace",
            )

            summary = result.summary.to_dict()
            failure_modes = [fm.to_dict() for fm in result.failure_modes]
            warnings = [w.to_dict() for w in result.validation_warnings]

            chash = _config_hash(config_dict)
            index.register(
                run_id=run_id,
                run_dir=str(output_dir),
                label=run_label,
                config_hash=chash,
                config_summary={
                    "baseline_type": config_dict.get("baseline_type"),
                    "oracle_mode": config_dict.get("oracle_mode"),
                    "sigma": config_dict.get("sigma"),
                    "seed": config_dict.get("seed"),
                },
                summary_metrics=summary,
            )

            return {
                "ok": True,
                "run_id": run_id,
                "run_dir": str(output_dir),
                "summary": summary,
                "failure_modes": failure_modes,
                "validation_warnings": warnings,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @mcp.tool(
        name="explain_concept",
        description="Look up a LIFLUCT domain concept (amm, lp, toxic_flow, attribution, best_fixed, lysis, regime, oracle).",
    )
    async def tool_explain_concept(concept: str) -> dict[str, Any]:
        try:
            return _explain_concept(concept)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ===================================================================
    # Tier 2: Configure & run custom experiments
    # ===================================================================

    @mcp.tool(
        name="configure_experiment",
        description="Build an experiment configuration dict with smart defaults. Returns JSON config.",
    )
    async def tool_configure_experiment(
        baseline_type: str = "dynamic_fee_single",
        oracle_mode: str = "perfect",
        oracle_lag_steps: int = 0,
        sigma: float = 0.02,
        num_steps: int = 1000,
        seed: int = 42,
        toxic_mode: str = "cheapest_active",
        use_dynamic_fee: bool = True,
        f_min: float = 0.003,
        mu: float = 0.15,
        tau: float = 0.002,
        beta: float = 0.0,
        lysis_mode: str = "off",
    ) -> dict[str, Any]:
        try:
            config = {
                **_BASE_CONFIG,
                "baseline_type": baseline_type,
                "oracle_mode": oracle_mode,
                "oracle_lag_steps": oracle_lag_steps,
                "sigma": sigma,
                "num_steps": num_steps,
                "seed": seed,
                "toxic_mode": toxic_mode,
                "use_dynamic_fee": use_dynamic_fee,
                "f_min": f_min,
                "mu": mu,
                "tau": tau,
                "beta": beta,
                "lysis_mode": lysis_mode,
            }
            return {"ok": True, "config": config, "config_hash": _config_hash(config)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @mcp.tool(
        name="validate_config",
        description="Validate an experiment config JSON string for consistency issues.",
    )
    async def tool_validate_config(config: str) -> dict[str, Any]:
        try:
            cfg = json.loads(config)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON: {e}"}

        try:
            issues: list[str] = []

            # Check for required fields
            required = ["baseline_type", "sigma", "num_steps", "seed"]
            for field in required:
                if field not in cfg:
                    issues.append(f"Missing required field: {field}")

            # Consistency checks
            if cfg.get("oracle_mode") == "lagged" and cfg.get("oracle_lag_steps", 0) == 0:
                issues.append("oracle_mode='lagged' but oracle_lag_steps=0 — lag has no effect.")

            if cfg.get("oracle_mode") == "perfect" and cfg.get("oracle_lag_steps", 0) > 0:
                issues.append("oracle_mode='perfect' ignores oracle_lag_steps — set mode to 'lagged' to use lag.")

            if cfg.get("use_dynamic_fee") is False and cfg.get("mu", 0) > 0:
                issues.append("use_dynamic_fee=False but mu>0 — mu has no effect without dynamic fees.")

            if cfg.get("baseline_type") == "static_cpmm" and cfg.get("use_dynamic_fee") is True:
                issues.append("baseline_type='static_cpmm' with use_dynamic_fee=True — these conflict.")

            if cfg.get("lysis_mode", "off") != "off" and not cfg.get("use_turgor", False):
                issues.append("lysis_mode is set but use_turgor=False — lysis requires turgor mode.")

            sigma = cfg.get("sigma", 0)
            if isinstance(sigma, (int, float)) and sigma > 0.2:
                issues.append(f"sigma={sigma} is very high — typical range is 0.01-0.10.")

            num_steps = cfg.get("num_steps", 0)
            if isinstance(num_steps, (int, float)) and num_steps > 50000:
                issues.append(f"num_steps={num_steps} will be slow — consider <10000 for exploration.")

            return {
                "ok": len(issues) == 0,
                "issues": issues,
                "config": cfg,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @mcp.tool(
        name="run_experiment",
        description="Run a simulation from a JSON config string. Returns summary, failure modes, and run_id.",
    )
    async def tool_run_experiment(
        config: str, label: str = "", retention_mode: str = "full_trace",
    ) -> dict[str, Any]:
        try:
            from lifluct.cli.run_simulation import execute_and_write_run
            from lifluct.types import RunConfig

            cfg = json.loads(config)
            rc = RunConfig.from_mapping(cfg)

            ts = _timestamp()
            chash = _config_hash(cfg)
            run_id = f"exp_{chash}_{ts}"
            run_label = label or f"custom:{chash}"
            output_dir = Path(runs_dir) / run_id
            output_dir.mkdir(parents=True, exist_ok=True)

            result = execute_and_write_run(
                config=rc, output_dir=output_dir, retention_mode=retention_mode,
            )

            summary = result.summary.to_dict()
            failure_modes = [fm.to_dict() for fm in result.failure_modes]
            warnings = [w.to_dict() for w in result.validation_warnings]

            index.register(
                run_id=run_id,
                run_dir=str(output_dir),
                label=run_label,
                config_hash=chash,
                config_summary={
                    "baseline_type": cfg.get("baseline_type"),
                    "oracle_mode": cfg.get("oracle_mode"),
                    "sigma": cfg.get("sigma"),
                    "seed": cfg.get("seed"),
                },
                summary_metrics=summary,
            )

            return {
                "ok": True,
                "run_id": run_id,
                "run_dir": str(output_dir),
                "summary": summary,
                "failure_modes": failure_modes,
                "validation_warnings": warnings,
            }
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON config: {e}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ===================================================================
    # Tier 3: Inspect & compare results
    # ===================================================================

    @mcp.tool(
        name="read_results",
        description="Read summary, failure modes, and diagnostics from a completed run. Provide run_id or run_dir.",
    )
    async def tool_read_results(run_id: str = "", run_dir: str = "") -> dict[str, Any]:
        try:
            if not run_id and not run_dir:
                return {"ok": False, "error": "Provide either run_id or run_dir."}

            if run_id and not run_dir:
                run_info = index.get_run(run_id)
                if run_info is None:
                    return {"ok": False, "error": f"Run {run_id!r} not found in index."}
                run_dir = run_info["run_dir"]

            rd = Path(run_dir)
            if not rd.is_dir():
                return {"ok": False, "error": f"Run directory does not exist: {run_dir}"}

            result: dict[str, Any] = {"ok": True, "run_dir": str(rd)}

            for fname in ["summary.json", "failure_modes.json", "validation_warnings.json", "diagnostics.json"]:
                fpath = rd / fname
                key = fname.replace(".json", "")
                if fpath.exists():
                    result[key] = json.loads(fpath.read_text(encoding="utf-8"))
                else:
                    result[key] = None

            # List available artifacts
            result["available_artifacts"] = sorted(
                str(p.relative_to(rd)) for p in rd.rglob("*") if p.is_file()
            )
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @mcp.tool(
        name="list_runs",
        description="List tracked experiment runs from the index. Optionally filter by label substring.",
    )
    async def tool_list_runs(filter_label: str = "", limit: int = 50) -> dict[str, Any]:
        try:
            runs = index.list_runs(
                filter_label=filter_label or None, limit=limit,
            )
            return {"ok": True, "runs": runs, "count": len(runs)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @mcp.tool(
        name="compare_runs",
        description="Compare multiple runs by their summary metrics. Pass comma-separated run IDs.",
    )
    async def tool_compare_runs(run_ids: str = "") -> dict[str, Any]:
        try:
            if not run_ids.strip():
                return {"ok": False, "error": "Provide comma-separated run_ids."}

            ids = [rid.strip() for rid in run_ids.split(",") if rid.strip()]
            if len(ids) < 2:
                return {"ok": False, "error": "Need at least 2 run IDs to compare."}

            rows: list[dict[str, Any]] = []
            for rid in ids:
                run_info = index.get_run(rid)
                if run_info is None:
                    return {"ok": False, "error": f"Run {rid!r} not found in index."}
                rows.append({
                    "run_id": rid,
                    "label": run_info["label"],
                    "config_summary": run_info["config_summary"],
                    "summary_metrics": run_info["summary_metrics"],
                })

            # Determine winner by lp_minus_hodl_b
            scored = [
                (r, r["summary_metrics"].get("lp_minus_hodl_b"))
                for r in rows
            ]
            scored_valid = [(r, s) for r, s in scored if s is not None]
            winner = None
            if scored_valid:
                best = max(scored_valid, key=lambda x: x[1])
                winner = {"run_id": best[0]["run_id"], "lp_minus_hodl_b": best[1]}

            return {
                "ok": True,
                "runs": rows,
                "winner": winner,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @mcp.tool(
        name="read_attribution_robustness",
        description="Read attribution mode comparison and ranking stability from a completed run.",
    )
    async def tool_read_attribution_robustness(run_id: str) -> dict[str, Any]:
        try:
            run_info = index.get_run(run_id)
            if run_info is None:
                return {"ok": False, "error": f"Run {run_id!r} not found in index."}

            rd = Path(run_info["run_dir"])
            if not rd.is_dir():
                return {"ok": False, "error": f"Run directory does not exist: {run_info['run_dir']}"}

            result: dict[str, Any] = {"ok": True, "run_id": run_id}

            comparison_path = rd / "attribution_mode_comparison.json"
            if comparison_path.exists():
                result["attribution_mode_comparison"] = json.loads(
                    comparison_path.read_text(encoding="utf-8")
                )
            else:
                result["attribution_mode_comparison"] = None

            ranking_path = rd / "attribution_ranking_stability.json"
            if ranking_path.exists():
                result["attribution_ranking_stability"] = json.loads(
                    ranking_path.read_text(encoding="utf-8")
                )
            else:
                result["attribution_ranking_stability"] = None

            if result["attribution_mode_comparison"] is None and result["attribution_ranking_stability"] is None:
                result["note"] = (
                    "No attribution robustness data found. This is generated only "
                    "when full_trace retention is used and the run has sufficient data."
                )

            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ===================================================================
    # Tier 4: Advisor
    # ===================================================================

    @mcp.tool(
        name="suggest_next_experiment",
        description="Analyze completed runs and recommend what experiment to run next. Pass comma-separated run IDs (or empty for no-run advice).",
    )
    async def tool_suggest_next_experiment(run_ids: str = "") -> dict[str, Any]:
        try:
            if not run_ids.strip():
                return {"ok": True, **suggest_next([])}

            ids = [rid.strip() for rid in run_ids.split(",") if rid.strip()]
            run_data: list[dict[str, Any]] = []
            for rid in ids:
                run_info = index.get_run(rid)
                if run_info is None:
                    return {"ok": False, "error": f"Run {rid!r} not found in index."}

                entry: dict[str, Any] = {
                    "run_id": rid,
                    "config_summary": run_info["config_summary"],
                    "summary_metrics": run_info["summary_metrics"],
                    "failure_modes": [],
                }

                # Try to load failure_modes from disk
                rd = Path(run_info["run_dir"])
                fm_path = rd / "failure_modes.json"
                if fm_path.exists():
                    entry["failure_modes"] = json.loads(fm_path.read_text(encoding="utf-8"))

                run_data.append(entry)

            suggestion = suggest_next(run_data)
            return {"ok": True, **suggestion}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="stdio", choices=["stdio"])
    args = parser.parse_args()
    server = create_server()
    server.run(transport=args.mode)


if __name__ == "__main__":
    main()
