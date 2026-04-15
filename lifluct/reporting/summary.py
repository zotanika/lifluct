"""Markdown report writers for LIFLUCT runs and experiments."""

from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Sequence

from lifluct.reporting.tables import bullet_list
from lifluct.types import (
    CellSnapshot,
    EpochSummary,
    FailureModeObservation,
    RunConfig,
    RunSummary,
    ValidationWarning,
)


def write_run_summary_markdown(
    output_path: str | Path,
    config: RunConfig,
    summary: RunSummary,
    plot_paths: dict[str, Path],
    run_dir: str | Path,
    *,
    retention_mode: str = "full_trace",
    available_artifacts: Sequence[str] | None = None,
    epoch_summaries: Sequence[EpochSummary] | None = None,
    cell_snapshots: Sequence[CellSnapshot] | None = None,
    validation_warnings: Sequence[ValidationWarning] | None = None,
    failure_modes: Sequence[FailureModeObservation] | None = None,
) -> Path:
    template = _load_template("run_summary_template.md")
    output = Path(output_path)
    report_dir = output.parent
    epoch_summaries = epoch_summaries or []
    validation_warnings = validation_warnings or []
    failure_modes = failure_modes or []
    available_artifacts = available_artifacts or []

    config_block = bullet_list(
        [
            f"baseline_type: `{config.baseline_type}`",
            f"seed: `{config.seed}`",
            f"num_steps: `{config.num_steps}`",
            f"epoch_length: `{config.epoch_length}`",
            f"num_cells: `{config.num_cells}`",
            f"oracle_mode: `{config.oracle_mode}`",
            f"oracle_lag_steps: `{config.oracle_lag_steps}`",
            f"sigma: `{config.sigma}`",
            f"user_routing_mode: `{config.user_routing_mode}`",
            f"toxic_mode: `{config.toxic_mode or config.toxic_routing_mode}`",
            f"fitness_mode: `{config.fitness_mode}`",
            f"lysis_mode: `{config.lysis_mode}`",
            f"attribution_mode: `{config.attribution_mode}`",
            f"use_dynamic_fee: `{config.use_dynamic_fee}`",
            f"use_turgor: `{config.use_turgor}`",
        ]
    )

    metrics_block = bullet_list(
        [
            f"final_lp_value_b: `{summary.final_lp_value_b:.6f}`",
            f"final_hodl_value_b: `{summary.final_hodl_value_b:.6f}`",
            f"lp_minus_hodl_b: `{summary.lp_minus_hodl_b:.6f}`",
            f"total_lp_revenue_b: `{summary.total_lp_revenue_b:.6f}`",
            f"total_protocol_revenue_b: `{summary.total_protocol_revenue_b:.6f}`",
            f"total_attributed_loss_b: `{summary.total_attributed_loss_b:.6f}`",
            f"total_trader_cost_b: `{summary.total_trader_cost_b:.6f}`",
            f"total_arbitrage_profit_b: `{summary.total_arbitrage_profit_b:.6f}`",
            f"total_lysis_count: `{summary.total_lysis_count}`",
            f"total_dead_cells: `{summary.total_dead_cells}`",
            f"num_trades: `{summary.num_trades}`",
            f"num_noise_trades: `{summary.num_noise_trades}`",
            f"num_arbitrage_trades: `{summary.num_arbitrage_trades}`",
        ]
    )

    output_paths_block = bullet_list(
        [
            "run_dir: `.`",
            f"retention_mode: `{retention_mode}`",
            *[f"artifact: `{artifact}`" for artifact in available_artifacts],
            *[
                f"plot_{plot_name}: `{_relative_display_path(plot_path, report_dir)}`"
                for plot_name, plot_path in plot_paths.items()
            ],
        ]
    )

    final_epoch_block = "_No epoch summaries available._"
    if epoch_summaries:
        latest_epoch = epoch_summaries[-1]
        final_epoch_block = bullet_list(
            [
                f"epoch_index: `{latest_epoch.epoch_index}`",
                f"num_active_cells: `{latest_epoch.num_active_cells}`",
                f"num_lysed_cells: `{latest_epoch.num_lysed_cells}`",
                f"num_dead_cells: `{latest_epoch.num_dead_cells}`",
                f"mean_fitness: `{latest_epoch.mean_fitness:.6f}`",
                f"median_fitness: `{latest_epoch.median_fitness:.6f}`",
                f"top_cell_ids: `{latest_epoch.top_cell_ids}`",
            ]
        )

    warnings_block = bullet_list(
        [f"[{warning.severity}] {warning.message}" for warning in validation_warnings]
    )
    failure_modes_block = bullet_list(
        [
            (
                f"`{mode.mode}` ({mode.severity}, heuristic): {mode.evidence}"
                + (f" Trigger: {mode.trigger_heuristic}." if mode.trigger_heuristic else "")
            )
            for mode in failure_modes
        ]
    )
    notes_block = bullet_list(
        [
            "This remains a toy-model research simulator.",
            "Local attributed loss is still a heuristic proxy, not an exact LVR measure.",
            "Stronger adversary modes are stylized approximations, not complete market microstructure models.",
            "Lysis is heuristic and can produce false positives.",
            "Negative or failure regimes are expected and informative rather than a bug in the research process.",
        ]
    )

    rendered = template.safe_substitute(
        title="LIFLUCT Run Summary",
        config_block=config_block,
        metrics_block=metrics_block,
        output_paths_block=output_paths_block,
        final_epoch_block=final_epoch_block,
        warnings_block=warnings_block,
        failure_modes_block=failure_modes_block,
        notes_block=notes_block,
    )
    output.write_text(rendered, encoding="utf-8")
    return output


def write_comparison_report_markdown(
    output_path: str | Path,
    *,
    title: str,
    regime_definition_block: str,
    model_family_block: str,
    comparison_table: str,
    aggregated_table: str,
    heuristic_failure_flags: Sequence[str],
    validation_warnings: Sequence[str],
    statistical_notes: Sequence[str],
    plot_paths: dict[str, Path],
    key_observations: Sequence[str],
    attribution_robustness_block: str = "_No attribution robustness analysis available._",
) -> Path:
    template = _load_template("comparison_report_template.md")
    output = Path(output_path)
    report_dir = output.parent
    rendered = template.safe_substitute(
        title=title,
        regime_definition_block=regime_definition_block,
        model_family_block=model_family_block,
        comparison_table=comparison_table,
        aggregated_table=aggregated_table,
        heuristic_failure_flags_block=bullet_list(list(heuristic_failure_flags)),
        validation_warnings_block=bullet_list(list(validation_warnings)),
        statistical_notes_block=bullet_list(list(statistical_notes)),
        plots_block=bullet_list(
            [f"`{name}`: `{_relative_display_path(path, report_dir)}`" for name, path in plot_paths.items()]
        ),
        key_observations_block=bullet_list(list(key_observations)),
        attribution_robustness_block=attribution_robustness_block,
    )
    output.write_text(rendered, encoding="utf-8")
    return output


def write_failure_report_markdown(
    output_path: str | Path,
    *,
    title: str,
    regime_definition_block: str,
    model_family_block: str,
    failure_mode_rows: Sequence[str],
    warnings_rows: Sequence[str],
    weak_result_rows: Sequence[str],
    plots_block: Sequence[str],
) -> Path:
    template = _load_template("failure_report_template.md")
    output = Path(output_path)
    rendered = template.safe_substitute(
        title=title,
        regime_definition_block=regime_definition_block,
        model_family_block=model_family_block,
        heuristic_failure_flags_block=bullet_list(list(failure_mode_rows)),
        warnings_block=bullet_list(list(warnings_rows)),
        weak_results_block=bullet_list(list(weak_result_rows)),
        plots_block=bullet_list(list(plots_block)),
    )
    output.write_text(rendered, encoding="utf-8")
    return output


def _relative_display_path(path: str | Path, base_dir: str | Path) -> str:
    target = Path(path)
    base = Path(base_dir)
    try:
        return str(target.relative_to(base))
    except ValueError:
        try:
            return str(target.resolve().relative_to(base.resolve()))
        except ValueError:
            return str(Path("..") / target.name) if target.is_absolute() else str(target)


def _load_template(template_name: str) -> Template:
    template_path = Path(__file__).resolve().parents[2] / "reports" / "templates" / template_name
    return Template(template_path.read_text(encoding="utf-8"))
