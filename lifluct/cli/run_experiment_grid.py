"""Run an experiment grid and generate aggregate research outputs."""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from lifluct.cli.run_simulation import execute_and_write_run
from lifluct.constants import DEFAULT_OUTPUT_DIR
from lifluct.reporting.compare import generate_comparison_outputs, load_runs
from lifluct.reporting.experiment_registry import append_registry_records, make_registry_record, write_registry
from lifluct.reporting.loader import load_run_config
from lifluct.reporting.research_report import (
    write_attribution_robustness_report_markdown,
    write_frontier_report_markdown,
    write_thesis_adjudication_report_markdown,
)
from lifluct.reporting.summary import write_comparison_report_markdown, write_failure_report_markdown
from lifluct.types import RunConfig


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("grid", help=__doc__)
    parser.add_argument("--config", required=True, help="Path to an experiment-grid YAML definition")
    parser.add_argument("--output-dir", help="Optional experiment output directory")
    parser.add_argument(
        "--num-seeds",
        type=int,
        help="Optional override that expands seeds to range(1, num_seeds + 1)",
    )
    parser.set_defaults(func=_run)


def _run(args) -> None:
    config_path = Path(args.config)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    experiment_id = raw.get("experiment_id") or datetime.now().strftime("experiment_%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else Path(DEFAULT_OUTPUT_DIR) / "experiments" / experiment_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "runs").mkdir(parents=True, exist_ok=True)
    (output_dir / "experiment_config.yaml").write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")

    config_entries = _load_config_entries(raw, config_path.parent)
    sweep_spec = raw.get("sweep", {})
    seeds = list(range(1, args.num_seeds + 1)) if args.num_seeds else raw.get("seeds")
    group_by = raw.get("group_by", ["label"])
    if isinstance(group_by, str):
        group_by = [group_by]

    registry_records = []
    run_dirs: list[Path] = []

    sweep_keys = sorted(sweep_spec.keys())
    sweep_values = list(itertools.product(*(sweep_spec[key] for key in sweep_keys))) or [()]

    run_index = 0
    for entry in config_entries:
        for values in sweep_values:
            overrides = dict(zip(sweep_keys, values, strict=True))
            comparison_label = _comparison_label(entry["label"], overrides)
            run_seeds = seeds or [entry["config"].seed]
            for seed in run_seeds:
                run_id = f"run_{run_index:04d}"
                run_index += 1
                run_dir = output_dir / "runs" / run_id
                run_config = replace(entry["config"], **entry["overrides"], **overrides, seed=seed)
                metadata = {
                    "experiment_id": experiment_id,
                    "run_id": run_id,
                    "label": comparison_label,
                    "seed": seed,
                    "overrides": overrides,
                    "model_type": entry.get("model_type") or run_config.baseline_type,
                }
                result = execute_and_write_run(run_config, run_dir, metadata=metadata)
                registry_records.append(
                    make_registry_record(
                        experiment_id=experiment_id,
                        run_id=run_id,
                        run_dir=run_dir,
                        label=comparison_label,
                        config=result.config,
                        summary=result.summary,
                        cell_snapshots=result.cell_snapshots,
                        warnings_count=len(result.validation_warnings),
                        failure_modes_count=len(result.failure_modes),
                        failure_modes=result.failure_modes,
                        model_type=metadata["model_type"],
                    )
                )
                run_dirs.append(run_dir)

    registry_path = write_registry(output_dir / "registry.csv", registry_records)
    append_registry_records(Path(DEFAULT_OUTPUT_DIR) / "experiment_registry.csv", registry_records)

    run_payloads = load_runs(run_dirs)
    comparison_outputs = generate_comparison_outputs(run_payloads, output_dir=output_dir, group_by=group_by)
    write_comparison_report_markdown(
        output_dir / "comparison_report.md",
        title=f"Experiment Comparison Report: {experiment_id}",
        regime_definition_block=comparison_outputs["regime_definition_block"],
        model_family_block=comparison_outputs["model_family_block"],
        comparison_table=comparison_outputs["comparison_table"],
        aggregated_table=comparison_outputs["aggregated_table"],
        heuristic_failure_flags=comparison_outputs["heuristic_failure_flags"],
        validation_warnings=comparison_outputs["validation_warnings"],
        statistical_notes=comparison_outputs["statistical_notes"],
        plot_paths=comparison_outputs["plot_paths"],
        key_observations=comparison_outputs["key_observations"],
        attribution_robustness_block=comparison_outputs["attribution_robustness_table"],
    )
    write_failure_report_markdown(
        output_dir / "failure_report.md",
        title=f"Failure-Regime Report: {experiment_id}",
        regime_definition_block=comparison_outputs["regime_definition_block"],
        model_family_block=comparison_outputs["model_family_block"],
        failure_mode_rows=comparison_outputs["heuristic_failure_flags"],
        warnings_rows=comparison_outputs["validation_warnings"],
        weak_result_rows=comparison_outputs["weak_results"],
        plots_block=[f"`{name}`: `{Path(path).name if Path(path).is_absolute() else path}`" for name, path in comparison_outputs["plot_paths"].items()],
    )
    write_frontier_report_markdown(
        output_dir / "frontier_report.md",
        title=f"Frontier Report: {experiment_id}",
        regime_definition_block=comparison_outputs["regime_definition_block"],
        model_family_block=comparison_outputs["model_family_block"],
        frontier_table=comparison_outputs["frontier_table"],
        observations=comparison_outputs["frontier_observations"],
        plot_paths=comparison_outputs["plot_paths"],
    )
    write_attribution_robustness_report_markdown(
        output_dir / "attribution_robustness_report.md",
        title=f"Attribution Robustness Report: {experiment_id}",
        regime_definition_block=comparison_outputs["regime_definition_block"],
        model_family_block=comparison_outputs["model_family_block"],
        robustness_table=comparison_outputs["attribution_robustness_table"],
        observations=comparison_outputs["attribution_robustness_observations"],
        plot_paths={
            key: path
            for key, path in comparison_outputs["plot_paths"].items()
            if "attribution" in key
        },
    )
    write_thesis_adjudication_report_markdown(
        output_dir / "thesis_adjudication_report.md",
        title=f"Thesis Adjudication Report: {experiment_id}",
        regime_definition_block=comparison_outputs["regime_definition_block"],
        model_family_block=comparison_outputs["model_family_block"],
        rows=comparison_outputs["rows"],
        frontier_observations=comparison_outputs["frontier_observations"],
        heuristic_failure_flags=comparison_outputs["heuristic_failure_flags"],
        validation_warnings=comparison_outputs["validation_warnings"],
        statistical_notes=comparison_outputs["statistical_notes"],
        attribution_robustness_block=comparison_outputs["attribution_robustness_table"],
        plot_paths=comparison_outputs["plot_paths"],
    )
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(
            {
                "experiment_id": experiment_id,
                "registry": str(registry_path),
                "num_runs": len(run_dirs),
                "group_by": group_by,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(output_dir)


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to an experiment-grid YAML definition")
    parser.add_argument("--output-dir", help="Optional experiment output directory")
    parser.add_argument(
        "--num-seeds",
        type=int,
        help="Optional override that expands seeds to range(1, num_seeds + 1)",
    )
    args = parser.parse_args()
    _run(args)


def _load_config_entries(raw: dict[str, Any], base_dir: Path) -> list[dict[str, Any]]:
    entries = raw.get("configs")
    if not entries:
        base_config = raw.get("base_config")
        if base_config is None:
            raise ValueError("experiment grid must define `configs` or `base_config`")
        entries = [base_config]

    loaded_entries = []
    for entry in entries:
        if isinstance(entry, str):
            config_path = base_dir / entry
            loaded_entries.append(
                {
                    "label": config_path.stem,
                    "config": load_run_config(config_path),
                    "overrides": {},
                    "model_type": None,
                }
            )
            continue
        if isinstance(entry, dict) and "path" in entry:
            config_path = base_dir / entry["path"]
            loaded_entries.append(
                {
                    "label": entry.get("label", Path(entry["path"]).stem),
                    "config": load_run_config(config_path),
                    "overrides": entry.get("overrides", {}),
                    "model_type": entry.get("model_type"),
                }
            )
            continue
        if isinstance(entry, dict):
            loaded_entries.append(
                {
                    "label": entry.get("label", "config"),
                    "config": RunConfig.from_mapping(entry.get("config", entry)),
                    "overrides": entry.get("overrides", {}),
                    "model_type": entry.get("model_type"),
                }
            )
            continue
        raise ValueError(f"unsupported config entry: {entry}")
    return loaded_entries


def _comparison_label(base_label: str, overrides: dict[str, Any]) -> str:
    if not overrides:
        return base_label
    suffix = ", ".join(f"{key}={value}" for key, value in sorted(overrides.items()))
    return f"{base_label} | {suffix}"


if __name__ == "__main__":
    main()
