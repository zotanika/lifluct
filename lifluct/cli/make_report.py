"""Regenerate plots and markdown summary for an existing run directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lifluct.core.attribution_modes import evaluate_attribution_modes, ranking_stability
from lifluct.core.diagnostics import summarize_result_diagnostics
from lifluct.constants import DEFAULT_PLOTS_DIRNAME
from lifluct.reporting.loader import load_run_directory
from lifluct.reporting.metrics import build_summary_from_outputs
from lifluct.reporting.plots import generate_all_plots, plot_attribution_mode_ranking_stability
from lifluct.reporting.summary import write_run_summary_markdown
from lifluct.reporting.validation import validate_loaded_run


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("report", help=__doc__)
    parser.add_argument("--run-dir", required=True, help="Path to an existing run directory")
    parser.set_defaults(func=_run)


def _run(args) -> None:
    run_dir = Path(args.run_dir)
    data = load_run_directory(run_dir)
    validation_warnings = data.get("validation_warnings")
    failure_modes = data.get("failure_modes")
    if validation_warnings is None or failure_modes is None:
        validation_warnings, failure_modes = validate_loaded_run(data)
        (run_dir / "validation_warnings.json").write_text(
            json.dumps([warning.to_dict() for warning in validation_warnings], indent=2) + "\n",
            encoding="utf-8",
        )
        (run_dir / "failure_modes.json").write_text(
            json.dumps([mode.to_dict() for mode in failure_modes], indent=2) + "\n",
            encoding="utf-8",
        )
    summary = data.get("summary") or build_summary_from_outputs(
        config=data["config"],
        trades=data["trades"],
        step_metrics=data["step_metrics"],
        epoch_summaries=data.get("epoch_summaries"),
        cell_snapshots=data.get("cell_snapshots"),
    )
    plot_paths = generate_all_plots(
        data["step_metrics"],
        run_dir / DEFAULT_PLOTS_DIRNAME,
        epoch_summaries=data.get("epoch_summaries"),
        cell_snapshots=data.get("cell_snapshots"),
    )
    diagnostics = summarize_result_diagnostics(
        config=data["config"],
        summary=summary,
        epoch_summaries=data.get("epoch_summaries", []),
        cell_snapshots=data.get("cell_snapshots", []),
        step_metrics=data["step_metrics"],
    )
    (run_dir / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8")
    if data.get("cell_snapshots") and data.get("trades") and data.get("step_metrics"):
        attribution_results = evaluate_attribution_modes(
            config=data["config"],
            trades=data["trades"],
            step_metrics=data["step_metrics"],
            cell_snapshots=data["cell_snapshots"],
        )
        attribution_payload = {
            mode: {
                "cell_loss_b": result.cell_loss_b,
                "cell_fitness": result.cell_fitness,
                "loss_ranking": result.loss_ranking,
                "fitness_ranking": result.fitness_ranking,
            }
            for mode, result in attribution_results.items()
        }
        (run_dir / "attribution_mode_comparison.json").write_text(
            json.dumps(attribution_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        ranking_rows = ranking_stability(attribution_results)
        (run_dir / "attribution_ranking_stability.json").write_text(
            json.dumps(ranking_rows, indent=2) + "\n",
            encoding="utf-8",
        )
        plot_paths["attribution_mode_ranking_stability"] = plot_attribution_mode_ranking_stability(
            ranking_rows,
            run_dir / DEFAULT_PLOTS_DIRNAME / "attribution_mode_ranking_stability.png",
        )
    write_run_summary_markdown(
        output_path=run_dir / "summary.md",
        config=data["config"],
        summary=summary,
        plot_paths=plot_paths,
        run_dir=run_dir,
        epoch_summaries=data.get("epoch_summaries"),
        cell_snapshots=data.get("cell_snapshots"),
        validation_warnings=validation_warnings,
        failure_modes=failure_modes,
    )
    print(run_dir / "summary.md")


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, help="Path to an existing run directory")
    args = parser.parse_args()
    _run(args)


if __name__ == "__main__":
    main()
