"""Generate a Phase 4.2 master adjudication report from completed family outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from lifluct.reporting.regime_reports import write_adjudication_master_markdown
from lifluct.reporting.tables import markdown_table


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("adjudicate", help=__doc__)
    parser.add_argument("--root-dir", required=True, help="Phase 4.2 root directory containing family subdirectories")
    parser.add_argument("--output-dir", help="Optional output directory for the master report")
    parser.set_defaults(func=_run)


def _run(args) -> None:
    root_dir = Path(args.root_dir)
    output_dir = Path(args.output_dir) if args.output_dir else root_dir / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    family_rows = load_family_verdict_rows(root_dir)
    write_adjudication_master_markdown(
        output_dir / "thesis_adjudication_master.md",
        title="Phase 4.2 Thesis Adjudication Master Report",
        family_table=markdown_table(family_rows),
        verdict_notes=[
            "Verdicts are assigned at the regime-family level.",
            "A few smoke runs are not evidence; aggregated family statistics are the intended unit of interpretation.",
            "Attribution remains heuristic even when ranking stability looks strong.",
        ],
        plots_block=[
            f"`{row['family_name']}`: `{row['family_report_path']}`"
            for row in family_rows
        ],
    )
    print(output_dir)


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-dir", required=True, help="Phase 4.2 root directory containing family subdirectories")
    parser.add_argument("--output-dir", help="Optional output directory for the master report")
    args = parser.parse_args()
    _run(args)


def load_family_verdict_rows(root_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family_dir in sorted(path for path in root_dir.iterdir() if path.is_dir()):
        adjudication_path = family_dir / "aggregates" / "adjudication.json"
        aggregate_path = family_dir / "aggregates" / "aggregate_stats.csv"
        if not adjudication_path.exists():
            continue
        adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
        num_rows = 0
        attribution_stability = 0.0
        if aggregate_path.exists():
            with aggregate_path.open("r", encoding="utf-8", newline="") as handle:
                num_rows = sum(1 for _ in csv.DictReader(handle))
        attribution_path = family_dir / "reports" / "comparison_artifacts" / "attribution_robustness_aggregates.csv"
        if attribution_path.exists():
            with attribution_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            if rows:
                values = [
                    float(row["fitness_rank_correlation_mean"])
                    for row in rows
                    if row.get("fitness_rank_correlation_mean") not in {None, ""}
                ]
                if values:
                    attribution_stability = sum(values) / len(values)
        rows.append(
            {
                "family_name": adjudication["family_name"],
                "verdict": adjudication["verdict"],
                "sample_count": adjudication.get("sample_count", 0),
                "num_aggregate_groups": num_rows,
                "lp_vs_dynamic_median_diff": adjudication.get("lp_vs_dynamic_median_diff", 0.0),
                "lp_vs_best_fixed_median_diff": adjudication.get("lp_vs_best_fixed_median_diff", 0.0),
                "trader_cost_vs_dynamic_median_diff": adjudication.get("trader_cost_vs_dynamic_median_diff", 0.0),
                "critical_failure_prevalence": adjudication.get("critical_failure_prevalence", 0.0),
                "attribution_rank_stability_mean": attribution_stability,
                "family_report_path": f"{family_dir.name}/reports/regime_family_report.md",
            }
        )
    return rows


if __name__ == "__main__":
    main()
