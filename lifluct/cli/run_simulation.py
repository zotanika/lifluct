"""Run one LIFLUCT simulation from a YAML config."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import yaml

from lifluct.baselines.dynamic_fee_single import run_dynamic_fee_single
from lifluct.baselines.static_cpmm import run_static_cpmm
from lifluct.baselines.lifluct_multi_cell import run_lifluct_multi_cell
from lifluct.constants import DEFAULT_OUTPUT_DIR, DEFAULT_PLOTS_DIRNAME
from lifluct.core.attribution_modes import evaluate_attribution_modes, ranking_stability
from lifluct.core.diagnostics import summarize_result_diagnostics
from lifluct.core.simulation import SimulationRunner
from lifluct.orchestration.retention import retention_artifacts
from lifluct.reporting.loader import load_run_config
from lifluct.reporting.plots import generate_all_plots, plot_attribution_mode_ranking_stability
from lifluct.reporting.research_report import write_attribution_robustness_report_markdown
from lifluct.reporting.summary import write_run_summary_markdown
from lifluct.reporting.validation import validate_result
from lifluct.types import RegimeConfig, RetentionMode, RunConfig, SimulationResult


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("run", help=__doc__)
    parser.add_argument("--config", required=True, help="Path to a YAML run config")
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Defaults to runs/<config_name>_<timestamp>",
    )
    parser.set_defaults(func=_run)


def _run(args) -> None:
    config_path = Path(args.config)
    config = load_run_config(config_path)
    output_dir = Path(args.output_dir) if args.output_dir else _default_output_dir(config_path)
    execute_and_write_run(config=config, output_dir=output_dir)
    print(output_dir)


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to a YAML run config")
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Defaults to runs/<config_name>_<timestamp>",
    )
    args = parser.parse_args()
    _run(args)


def run_from_config(config: RunConfig) -> SimulationResult:
    if config.baseline_type == "static_cpmm":
        return run_static_cpmm(config)
    if config.baseline_type == "dynamic_fee_single":
        return run_dynamic_fee_single(config)
    if config.baseline_type == "lifluct_multi_cell":
        return run_lifluct_multi_cell(config)
    return SimulationRunner(config).run_single()


def execute_and_write_run(
    config: RunConfig,
    output_dir: str | Path,
    *,
    metadata: dict[str, Any] | None = None,
    retention_mode: RetentionMode = "full_trace",
) -> SimulationResult:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    result = run_from_config(config)
    validation_warnings, failure_modes = validate_result(result)
    result.validation_warnings = validation_warnings
    result.failure_modes = failure_modes
    result.diagnostics = summarize_result_diagnostics(
        config=result.config,
        summary=result.summary,
        epoch_summaries=result.epoch_summaries,
        cell_snapshots=result.cell_snapshots,
        step_metrics=result.step_metrics,
    )
    artifact_policy = retention_artifacts(retention_mode)
    plots_dir = output_path / DEFAULT_PLOTS_DIRNAME
    available_artifacts = [
        "config_used.yaml",
        "summary.json",
        "validation_warnings.json",
        "failure_modes.json",
        "diagnostics.json",
    ]

    _write_yaml(output_path / "config_used.yaml", result.config.to_dict())
    if artifact_policy["write_trades"]:
        _write_csv(output_path / "trades.csv", result.trades)
        available_artifacts.append("trades.csv")
    if artifact_policy["write_step_metrics"]:
        _write_csv(output_path / "step_metrics.csv", result.step_metrics)
        available_artifacts.append("step_metrics.csv")
    if artifact_policy["write_epoch_summaries"]:
        _write_csv(output_path / "epoch_summaries.csv", result.epoch_summaries)
        available_artifacts.append("epoch_summaries.csv")
    if artifact_policy["write_cell_snapshots"]:
        _write_csv(output_path / "cell_snapshots.csv", result.cell_snapshots)
        available_artifacts.append("cell_snapshots.csv")
    (output_path / "summary.json").write_text(
        json.dumps(result.summary.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    (output_path / "validation_warnings.json").write_text(
        json.dumps([warning.to_dict() for warning in validation_warnings], indent=2) + "\n",
        encoding="utf-8",
    )
    (output_path / "failure_modes.json").write_text(
        json.dumps([mode.to_dict() for mode in failure_modes], indent=2) + "\n",
        encoding="utf-8",
    )
    (output_path / "diagnostics.json").write_text(
        json.dumps(result.diagnostics, indent=2) + "\n",
        encoding="utf-8",
    )
    attribution_ranking_rows: list[dict[str, float | str]] = []
    attribution_table = "_No attribution robustness analysis available._"
    if (
        artifact_policy["write_trades"]
        and artifact_policy["write_step_metrics"]
        and artifact_policy["write_cell_snapshots"]
        and result.cell_snapshots
        and result.trades
        and result.step_metrics
    ):
        attribution_results = evaluate_attribution_modes(
            config=result.config,
            trades=result.trades,
            step_metrics=result.step_metrics,
            cell_snapshots=result.cell_snapshots,
        )
        attribution_payload = {
            mode: {
                "cell_loss_b": data.cell_loss_b,
                "cell_fitness": data.cell_fitness,
                "loss_ranking": data.loss_ranking,
                "fitness_ranking": data.fitness_ranking,
            }
            for mode, data in attribution_results.items()
        }
        attribution_ranking_rows = ranking_stability(attribution_results)
        (output_path / "attribution_mode_comparison.json").write_text(
            json.dumps(attribution_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        (output_path / "attribution_ranking_stability.json").write_text(
            json.dumps(attribution_ranking_rows, indent=2) + "\n",
            encoding="utf-8",
        )
        available_artifacts.extend(
            [
                "attribution_mode_comparison.json",
                "attribution_ranking_stability.json",
            ]
        )
        attribution_table = (
            "| mode | loss_rank_correlation | fitness_rank_correlation |\n"
            "| --- | --- | --- |\n"
            + "\n".join(
                f"| {row['mode']} | {float(row['loss_rank_correlation']):.4f} | {float(row['fitness_rank_correlation']):.4f} |"
                for row in attribution_ranking_rows
            )
        )
    if metadata is not None:
        metadata = dict(metadata)
        metadata.setdefault("retention_mode", retention_mode)
        (output_path / "run_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )
        available_artifacts.append("run_metadata.json")
    plot_paths: dict[str, Path] = {}
    if artifact_policy["write_plots"] and artifact_policy["write_step_metrics"]:
        plot_paths = generate_all_plots(
            result.step_metrics,
            plots_dir,
            epoch_summaries=result.epoch_summaries if artifact_policy["write_epoch_summaries"] else [],
            cell_snapshots=result.cell_snapshots if artifact_policy["write_cell_snapshots"] else [],
        )
        available_artifacts.extend(str(path.relative_to(output_path)) for path in plot_paths.values())
    if artifact_policy["write_plots"] and attribution_ranking_rows:
        plot_paths["attribution_mode_ranking_stability"] = plot_attribution_mode_ranking_stability(
            attribution_ranking_rows,
            plots_dir / "attribution_mode_ranking_stability.png",
        )
        available_artifacts.append(str(plot_paths["attribution_mode_ranking_stability"].relative_to(output_path)))
        write_attribution_robustness_report_markdown(
            output_path / "attribution_robustness_report.md",
            title="Attribution Robustness Report",
            regime_definition_block=_single_run_regime_block(result.config),
            model_family_block=f"- `{_single_run_family(result.config)}`",
            robustness_table=attribution_table,
            observations=[
                "This report recomputes attributed loss and fitness under alternative reference-price modes on the same trade log.",
                "If rankings flip materially across modes, attribution-sensitive conclusions should be treated cautiously.",
            ],
            plot_paths={
                "attribution_mode_ranking_stability": plot_paths["attribution_mode_ranking_stability"],
            },
        )
        available_artifacts.append("attribution_robustness_report.md")
    write_run_summary_markdown(
        output_path=output_path / "summary.md",
        config=result.config,
        summary=result.summary,
        plot_paths=plot_paths,
        run_dir=output_path,
        retention_mode=retention_mode,
        available_artifacts=available_artifacts,
        epoch_summaries=result.epoch_summaries,
        cell_snapshots=result.cell_snapshots,
        validation_warnings=validation_warnings,
        failure_modes=failure_modes,
    )
    return result


def _single_run_regime_block(config: RunConfig) -> str:
    regime = RegimeConfig.from_run_config(config)
    return "\n".join(
        [
            f"- regime_id: `{regime.regime_id()}`",
            f"- sigma: `{regime.sigma}`",
            f"- oracle_mode: `{regime.oracle_mode}`",
            f"- oracle_lag_steps: `{regime.oracle_lag_steps}`",
            f"- user_routing_mode: `{regime.user_routing_mode}`",
            f"- toxic_mode: `{regime.toxic_mode}`",
            f"- lysis_mode: `{regime.lysis_mode}`",
        ]
    )


def _single_run_family(config: RunConfig) -> str:
    return "no_lysis" if config.lysis_mode == "off" else "lysis_enabled"


def _write_yaml(path: str | Path, payload: dict[str, Any]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def _write_csv(path: str | Path, records: Sequence[Any]) -> None:
    rows = [record.to_dict() for record in records]
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _default_output_dir(config_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(DEFAULT_OUTPUT_DIR) / f"{config_path.stem}_{timestamp}"


if __name__ == "__main__":
    main()
