"""Compare a set of runs or an experiment directory and emit markdown + plots."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from lifluct.constants import DEFAULT_OUTPUT_DIR
from lifluct.reporting.compare import (
    collect_run_dirs_from_experiment,
    generate_comparison_outputs,
    load_runs,
)
from lifluct.reporting.experiment_registry import load_registry_rows
from lifluct.reporting.research_report import (
    write_attribution_robustness_report_markdown,
    write_frontier_report_markdown,
    write_thesis_adjudication_report_markdown,
)
from lifluct.reporting.summary import write_comparison_report_markdown, write_failure_report_markdown


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("compare", help=__doc__)
    parser.add_argument("--run-dir", action="append", default=[], help="Run directory to compare")
    parser.add_argument("--experiment-dir", help="Experiment directory containing runs/")
    parser.add_argument("--registry", help="Registry CSV path")
    parser.add_argument("--experiment-id", help="Experiment id filter when using --registry")
    parser.add_argument("--run-id", action="append", default=[], help="Run id filter when using --registry")
    parser.add_argument("--group-by", default="label", help="Comma-separated grouping fields")
    parser.add_argument(
        "--family",
        choices=["all", "no_lysis", "lysis_enabled"],
        default="all",
        help="Optional model-family filter so no-lysis and lysis-enabled reports stay separate by default.",
    )
    parser.add_argument("--output-dir", help="Optional comparison output directory")
    parser.set_defaults(func=_run)


def _run(args) -> None:
    run_dirs = [Path(path) for path in args.run_dir]
    if args.experiment_dir:
        run_dirs.extend(collect_run_dirs_from_experiment(args.experiment_dir))
    if args.registry:
        run_dirs.extend(_run_dirs_from_registry(args.registry, experiment_id=args.experiment_id, run_ids=args.run_id))

    run_dirs = sorted({path for path in run_dirs})
    if not run_dirs:
        raise ValueError("No runs selected for comparison.")

    group_by = [field.strip() for field in args.group_by.split(",") if field.strip()]
    output_dir = Path(args.output_dir) if args.output_dir else Path(DEFAULT_OUTPUT_DIR) / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    run_payloads = load_runs(run_dirs)
    if args.family != "all":
        run_payloads = [payload for payload in run_payloads if _payload_family(payload) == args.family]
    if not run_payloads:
        raise ValueError("No runs remained after applying the family filter.")

    comparison_outputs = generate_comparison_outputs(run_payloads, output_dir=output_dir, group_by=group_by)
    write_comparison_report_markdown(
        output_dir / "comparison_report.md",
        title="Comparison Report",
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
        title="Failure-Regime Report",
        regime_definition_block=comparison_outputs["regime_definition_block"],
        model_family_block=comparison_outputs["model_family_block"],
        failure_mode_rows=comparison_outputs["heuristic_failure_flags"],
        warnings_rows=comparison_outputs["validation_warnings"],
        weak_result_rows=comparison_outputs["weak_results"],
        plots_block=[f"`{name}`: `{Path(path).name if Path(path).is_absolute() else path}`" for name, path in comparison_outputs["plot_paths"].items()],
    )
    write_frontier_report_markdown(
        output_dir / "frontier_report.md",
        title="Frontier Report",
        regime_definition_block=comparison_outputs["regime_definition_block"],
        model_family_block=comparison_outputs["model_family_block"],
        frontier_table=comparison_outputs["frontier_table"],
        observations=comparison_outputs["frontier_observations"],
        plot_paths=comparison_outputs["plot_paths"],
    )
    write_attribution_robustness_report_markdown(
        output_dir / "attribution_robustness_report.md",
        title="Attribution Robustness Report",
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
        title="Thesis Adjudication Report",
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
    print(output_dir)


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", action="append", default=[], help="Run directory to compare")
    parser.add_argument("--experiment-dir", help="Experiment directory containing runs/")
    parser.add_argument("--registry", help="Registry CSV path")
    parser.add_argument("--experiment-id", help="Experiment id filter when using --registry")
    parser.add_argument("--run-id", action="append", default=[], help="Run id filter when using --registry")
    parser.add_argument("--group-by", default="label", help="Comma-separated grouping fields")
    parser.add_argument(
        "--family",
        choices=["all", "no_lysis", "lysis_enabled"],
        default="all",
        help="Optional model-family filter so no-lysis and lysis-enabled reports stay separate by default.",
    )
    parser.add_argument("--output-dir", help="Optional comparison output directory")
    args = parser.parse_args()
    _run(args)


def _run_dirs_from_registry(
    registry_path: str | Path,
    *,
    experiment_id: str | None,
    run_ids: list[str],
) -> list[Path]:
    rows = load_registry_rows(registry_path)
    selected = []
    for row in rows:
        if experiment_id is not None and row.get("experiment_id") != experiment_id:
            continue
        if run_ids and row.get("run_id") not in run_ids:
            continue
        selected.append(Path(row["run_dir"]))
    return selected


def _payload_family(payload: dict[str, object]) -> str:
    config = payload["config"]
    return "no_lysis" if getattr(config, "lysis_mode") == "off" else "lysis_enabled"


if __name__ == "__main__":
    main()
