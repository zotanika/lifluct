"""Search for the best fixed single-cell policy and evaluate it with a train/test split."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from lifluct.cli.run_simulation import execute_and_write_run
from lifluct.constants import DEFAULT_OUTPUT_DIR
from lifluct.core.benchmark import (
    SERIOUS_SEARCH_BUDGET,
    SMOKE_SEARCH_BUDGET,
    build_fixed_single_cell_config,
    build_model_suite_for_regime,
    regime_for_family,
    search_best_fixed_single_cell,
)
from lifluct.reporting.compare import generate_comparison_outputs, load_runs
from lifluct.reporting.loader import load_run_config
from lifluct.reporting.research_report import (
    write_attribution_robustness_report_markdown,
    write_best_fixed_train_test_report_markdown,
    write_frontier_report_markdown,
    write_thesis_adjudication_report_markdown,
)
from lifluct.reporting.summary import write_comparison_report_markdown, write_failure_report_markdown
from lifluct.reporting.tables import markdown_table, write_rows_csv
from lifluct.types import ComparisonFamily, RegimeConfig, RunConfig


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("best-fixed", help=__doc__)
    parser.add_argument("--manifest", help="Optional YAML manifest describing train/test configs and search settings")
    parser.add_argument("--train-config", action="append", default=[], help="Train regime config path")
    parser.add_argument("--test-config", action="append", default=[], help="Optional test regime config path")
    parser.add_argument(
        "--search-profile",
        choices=["smoke", "serious"],
        default="serious",
        help="Smoke uses a small budget for quick checks; serious is the default for non-trivial benchmarking.",
    )
    parser.add_argument("--search-budget", type=int, help="Optional override for the fixed-policy search budget")
    parser.add_argument("--search-seed", type=int, default=7, help="Search RNG seed")
    parser.add_argument(
        "--objective-mode",
        default="lp_minus_hodl",
        choices=["lp_minus_hodl", "lp_minus_hodl_minus_trader_cost", "balanced"],
        help="Objective used to rank fixed candidates on the train set",
    )
    parser.add_argument(
        "--aggregate-mode",
        default="mean",
        choices=["mean", "median", "penalized_mean", "downside_robust"],
        help="How to aggregate train-set objective values across regimes and seeds.",
    )
    parser.add_argument(
        "--family",
        choices=["no_lysis", "lysis_enabled"],
        default="no_lysis",
        help="Comparison family to evaluate. Keep no-lysis and lysis-enabled suites separate.",
    )
    parser.add_argument("--output-dir", help="Optional output directory")
    parser.set_defaults(func=_run)


def _run(args) -> None:
    manifest_path = Path(args.manifest) if args.manifest else None
    manifest = _load_manifest(manifest_path) if manifest_path else {}
    manifest_base = manifest_path.parent if manifest_path is not None else Path.cwd()
    test_family_manifest = manifest.get("test_family_manifest")
    if test_family_manifest:
        nested_manifest = _load_manifest(_resolve_single_manifest_path(str(test_family_manifest), manifest_base))
        manifest.setdefault("test_configs", nested_manifest.get("test_configs", []))
    train_config_paths = _resolve_manifest_paths(args.train_config or manifest.get("train_configs", []), manifest_base)
    test_config_paths = _resolve_manifest_paths(args.test_config or manifest.get("test_configs", []), manifest_base)
    if not train_config_paths:
        raise ValueError("At least one train config is required.")

    search_profile = str(manifest.get("search_profile", args.search_profile))
    family = str(manifest.get("family", args.family))
    objective_mode = str(manifest.get("objective_mode", args.objective_mode))
    aggregate_mode = str(manifest.get("aggregate_mode", args.aggregate_mode))
    search_seed = int(manifest.get("search_seed", args.search_seed))
    default_budget = SMOKE_SEARCH_BUDGET if search_profile == "smoke" else SERIOUS_SEARCH_BUDGET
    search_budget = args.search_budget if args.search_budget is not None else int(manifest.get("search_budget", default_budget))

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path(DEFAULT_OUTPUT_DIR) / f"best_fixed_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    train_configs = [load_run_config(path) for path in train_config_paths]
    test_configs = [load_run_config(path) for path in test_config_paths]

    search_result = search_best_fixed_single_cell(
        train_configs=train_configs,
        search_budget=search_budget,
        objective_mode=objective_mode,
        search_seed=search_seed,
        test_configs=test_configs,
        search_profile=search_profile,
        family=family,  # type: ignore[arg-type]
        aggregate_mode=aggregate_mode,
    )

    write_rows_csv(output_dir / "search_results.csv", [candidate.to_dict() for candidate in search_result.candidates])
    write_rows_csv(output_dir / "train_evaluations.csv", search_result.train_rows)
    write_rows_csv(output_dir / "test_evaluations.csv", search_result.test_rows)

    reference_regime = regime_for_family(RegimeConfig.from_run_config(train_configs[0]), family)  # type: ignore[arg-type]
    best_config = build_fixed_single_cell_config(train_configs[0], search_result.best_genes, regime=reference_regime)
    with (output_dir / "best_candidate_config.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(best_config.to_dict(), handle, sort_keys=False)

    write_best_fixed_train_test_report_markdown(
        output_dir / "best_fixed_train_test_report.md",
        title="Best Fixed Single-Cell Train/Test Report",
        search_method=search_result.search_method,
        search_profile=search_result.search_profile,
        search_budget=search_result.search_budget,
        objective_mode=objective_mode,
        aggregate_mode=aggregate_mode,
        family=family,
        best_gene_block=markdown_table([search_result.best_genes.to_dict()]),
        in_sample_block=markdown_table(search_result.train_rows),
        out_of_sample_block=markdown_table(search_result.test_rows),
    )

    run_dirs: list[Path] = []
    evaluation_root = output_dir / "evaluation_runs"
    evaluation_root.mkdir(exist_ok=True)
    _execute_suite_runs(
        configs=train_configs,
        split="train",
        family=family,  # type: ignore[arg-type]
        best_fixed_genes=search_result.best_genes,
        evaluation_root=evaluation_root,
        run_dirs=run_dirs,
    )
    if test_configs:
        _execute_suite_runs(
            configs=test_configs,
            split="test",
            family=family,  # type: ignore[arg-type]
            best_fixed_genes=search_result.best_genes,
            evaluation_root=evaluation_root,
            run_dirs=run_dirs,
        )

    run_payloads = load_runs(run_dirs)
    comparison_outputs = generate_comparison_outputs(
        run_payloads,
        output_dir=output_dir,
        group_by=["evaluation_split", "model_type"],
    )
    write_rows_csv(output_dir / "suite_comparison.csv", comparison_outputs["rows"])

    write_comparison_report_markdown(
        output_dir / "comparison_report.md",
        title="Best Fixed Search Comparison Report",
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
        title="Best Fixed Search Failure Report",
        regime_definition_block=comparison_outputs["regime_definition_block"],
        model_family_block=comparison_outputs["model_family_block"],
        failure_mode_rows=comparison_outputs["heuristic_failure_flags"],
        warnings_rows=comparison_outputs["validation_warnings"],
        weak_result_rows=comparison_outputs["weak_results"],
        plots_block=[f"`{name}`: `{Path(path).name if Path(path).is_absolute() else path}`" for name, path in comparison_outputs["plot_paths"].items()],
    )
    write_frontier_report_markdown(
        output_dir / "frontier_report.md",
        title="Best Fixed Search Frontier Report",
        regime_definition_block=comparison_outputs["regime_definition_block"],
        model_family_block=comparison_outputs["model_family_block"],
        frontier_table=comparison_outputs["frontier_table"],
        observations=comparison_outputs["frontier_observations"],
        plot_paths=comparison_outputs["plot_paths"],
    )
    write_attribution_robustness_report_markdown(
        output_dir / "attribution_robustness_report.md",
        title="Best Fixed Search Attribution Robustness Report",
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
        title="Best Fixed Search Thesis Adjudication",
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
    (output_dir / "search_summary.json").write_text(
        json.dumps(
            {
                "objective_mode": objective_mode,
                "aggregate_mode": aggregate_mode,
                "search_budget": search_budget,
                "search_profile": search_profile,
                "search_method": search_result.search_method,
                "search_seed": search_seed,
                "comparison_family": family,
                "best_train_score": search_result.best_train_score,
                "best_genes": search_result.best_genes.to_dict(),
                "train_configs": [str(path) for path in train_config_paths],
                "test_configs": [str(path) for path in test_config_paths],
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
    parser.add_argument("--manifest", help="Optional YAML manifest describing train/test configs and search settings")
    parser.add_argument("--train-config", action="append", default=[], help="Train regime config path")
    parser.add_argument("--test-config", action="append", default=[], help="Optional test regime config path")
    parser.add_argument(
        "--search-profile",
        choices=["smoke", "serious"],
        default="serious",
        help="Smoke uses a small budget for quick checks; serious is the default for non-trivial benchmarking.",
    )
    parser.add_argument("--search-budget", type=int, help="Optional override for the fixed-policy search budget")
    parser.add_argument("--search-seed", type=int, default=7, help="Search RNG seed")
    parser.add_argument(
        "--objective-mode",
        default="lp_minus_hodl",
        choices=["lp_minus_hodl", "lp_minus_hodl_minus_trader_cost", "balanced"],
        help="Objective used to rank fixed candidates on the train set",
    )
    parser.add_argument(
        "--aggregate-mode",
        default="mean",
        choices=["mean", "median", "penalized_mean", "downside_robust"],
        help="How to aggregate train-set objective values across regimes and seeds.",
    )
    parser.add_argument(
        "--family",
        choices=["no_lysis", "lysis_enabled"],
        default="no_lysis",
        help="Comparison family to evaluate. Keep no-lysis and lysis-enabled suites separate.",
    )
    parser.add_argument("--output-dir", help="Optional output directory")
    args = parser.parse_args()
    _run(args)


def _execute_suite_runs(
    *,
    configs: list[RunConfig],
    split: str,
    family: ComparisonFamily,
    best_fixed_genes: Any,
    evaluation_root: Path,
    run_dirs: list[Path],
) -> None:
    for index, base_config in enumerate(configs):
        regime = regime_for_family(RegimeConfig.from_run_config(base_config), family)
        suite = build_model_suite_for_regime(
            template_config=base_config,
            regime=regime,
            family=family,
            best_fixed_genes=best_fixed_genes,
        )
        suite_id = f"{split}_{regime.regime_id()}"
        for model_type, config in suite.items():
            run_dir = evaluation_root / f"{split}_regime_{index:02d}_{model_type}"
            execute_and_write_run(
                config=config,
                output_dir=run_dir,
                metadata={
                    "label": model_type,
                    "model_type": model_type,
                    "model_family": family,
                    "evaluation_split": split,
                    "suite_id": suite_id,
                    "regime_id": regime.regime_id(),
                },
            )
            run_dirs.append(run_dir)


def _load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _resolve_manifest_paths(paths: list[str] | tuple[str, ...], base_dir: Path) -> list[str]:
    resolved: list[str] = []
    for raw_path in paths:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = base_dir / candidate
        resolved.append(str(candidate))
    return resolved


def _resolve_single_manifest_path(path: str, base_dir: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate


if __name__ == "__main__":
    main()
