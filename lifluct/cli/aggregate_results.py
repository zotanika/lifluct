"""Aggregate Phase 4.2 regime-family outputs into statistics and reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lifluct.reporting.aggregate_stats import add_comparator_summaries, aggregate_result_rows
from lifluct.reporting.adjudication import adjudicate_family
from lifluct.reporting.compare import collect_run_dirs_from_experiment, generate_comparison_outputs, load_runs
from lifluct.reporting.prevalence import failure_flag_prevalence
from lifluct.reporting.regime_reports import (
    write_adjudication_master_markdown,
    write_prevalence_report_markdown,
    write_regime_family_report_markdown,
)
from lifluct.reporting.tables import markdown_table, write_rows_csv


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("aggregate", help=__doc__)
    parser.add_argument("--family-dir", required=True, help="Path to a completed regime-family directory")
    parser.add_argument("--group-by", nargs="+", default=["model_type"], help="Aggregation grouping columns")
    parser.set_defaults(func=_run)


def _run(args) -> None:
    aggregate_family_directory(Path(args.family_dir), group_by=args.group_by)


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-dir", required=True, help="Path to a completed regime-family directory")
    parser.add_argument("--group-by", nargs="+", default=["model_type"], help="Aggregation grouping columns")
    args = parser.parse_args()
    _run(args)


def aggregate_family_directory(
    family_dir: str | Path,
    *,
    group_by: list[str] | None = None,
) -> dict[str, Any]:
    family_path = Path(family_dir)
    aggregates_dir = family_path / "aggregates"
    reports_dir = family_path / "reports"
    comparison_dir = reports_dir / "comparison_artifacts"
    aggregates_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    run_dirs = collect_run_dirs_from_experiment(family_path)
    run_payloads = load_runs(run_dirs)
    group_by = group_by or ["model_type"]
    comparison_outputs = generate_comparison_outputs(
        run_payloads,
        output_dir=comparison_dir,
        group_by=group_by,
    )
    aggregate_rows = aggregate_result_rows(comparison_outputs["rows"], group_by=group_by)
    prevalence_rows = failure_flag_prevalence(run_payloads, group_by="model_type")
    family_name = str(
        next(
            (
                payload.get("metadata", {}).get("experiment_family")
                for payload in run_payloads
                if payload.get("metadata", {}).get("experiment_family")
            ),
            family_path.name,
        )
    )
    model_family = _single_family(comparison_outputs["rows"])
    comparator_summary = {
        "lp_vs_dynamic": add_comparator_summaries(
            aggregate_rows,
            comparison_outputs["rows"],
            contender_model="lifluct_multi_cell_with_lysis" if model_family == "lysis_enabled" else "lifluct_multi_cell_no_lysis",
            comparator_model="dynamic_fee_single_with_lysis" if model_family == "lysis_enabled" else "dynamic_fee_single",
        )["lp_minus_hodl"],
        "lp_vs_best_fixed": add_comparator_summaries(
            aggregate_rows,
            comparison_outputs["rows"],
            contender_model="lifluct_multi_cell_with_lysis" if model_family == "lysis_enabled" else "lifluct_multi_cell_no_lysis",
            comparator_model="best_fixed_single_cell_with_lysis" if model_family == "lysis_enabled" else "best_fixed_single_cell",
        )["lp_minus_hodl"],
        "trader_vs_dynamic": add_comparator_summaries(
            aggregate_rows,
            comparison_outputs["rows"],
            contender_model="lifluct_multi_cell_with_lysis" if model_family == "lysis_enabled" else "lifluct_multi_cell_no_lysis",
            comparator_model="dynamic_fee_single_with_lysis" if model_family == "lysis_enabled" else "dynamic_fee_single",
        )["trader_cost"],
    }
    verdict = adjudicate_family(
        comparison_outputs["rows"],
        prevalence_rows,
        family_name=family_name,
        model_family=model_family,
    )

    write_rows_csv(aggregates_dir / "aggregate_stats.csv", aggregate_rows)
    write_rows_csv(aggregates_dir / "failure_prevalence.csv", prevalence_rows)
    (aggregates_dir / "adjudication.json").write_text(
        json.dumps(verdict.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    family_definition_block = "\n".join(
        [
            f"- family_name: `{family_name}`",
            f"- model_family: `{model_family}`",
            f"- num_runs: `{len(run_payloads)}`",
            f"- aggregation_group_by: `{', '.join(group_by)}`",
        ]
    )
    comparator_block = markdown_table([comparator_summary["lp_vs_dynamic"], comparator_summary["lp_vs_best_fixed"], comparator_summary["trader_vs_dynamic"]])
    verdict_block = "\n".join(
        [
            f"- verdict: `{verdict.verdict}`",
            *[f"- {reason}" for reason in verdict.reasons],
        ]
    )
    plot_lines = [
        f"`{name}`: `comparison_artifacts/plots/{Path(path).name}`"
        for name, path in comparison_outputs["plot_paths"].items()
    ]
    write_regime_family_report_markdown(
        reports_dir / "regime_family_report.md",
        title=f"Regime Family Report: {family_name}",
        family_definition_block=family_definition_block,
        aggregate_table=markdown_table(aggregate_rows),
        comparator_block=comparator_block,
        verdict_block=verdict_block,
        plots_block=plot_lines,
        notes=[
            "Verdicts are family-level summaries, not proofs.",
            "Negative or mixed outcomes remain first-class evidence.",
        ],
    )
    write_prevalence_report_markdown(
        reports_dir / "prevalence_report.md",
        title=f"Failure Prevalence Report: {family_name}",
        family_definition_block=family_definition_block,
        prevalence_table=markdown_table(prevalence_rows),
        notes=[
            "Failure flags are heuristic, not ground truth.",
            "High prevalence should be treated as structurally concerning even if some runs perform well.",
        ],
    )
    write_adjudication_master_markdown(
        reports_dir / "family_adjudication_report.md",
        title=f"Family Adjudication Summary: {family_name}",
        family_table=markdown_table([verdict.to_dict()]),
        verdict_notes=verdict.reasons,
        plots_block=plot_lines,
    )
    return {
        "family_name": family_name,
        "model_family": model_family,
        "aggregate_rows": aggregate_rows,
        "prevalence_rows": prevalence_rows,
        "verdict": verdict,
        "comparison_outputs": comparison_outputs,
    }


def _single_family(rows: list[dict[str, Any]]) -> str:
    families = sorted({str(row.get("model_family", "")) for row in rows})
    return families[0] if len(families) == 1 else "mixed"


if __name__ == "__main__":
    main()
