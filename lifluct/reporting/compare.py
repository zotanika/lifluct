"""Run-comparison helpers for fair regime-by-model research workflows."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from lifluct.core.attribution_modes import evaluate_attribution_modes, ranking_stability
from lifluct.core.diagnostics import summarize_result_diagnostics
from lifluct.constants import DEFAULT_PLOTS_DIRNAME, PLOT_FILE_NAMES
from lifluct.reporting.experiment_registry import final_gene_dispersion
from lifluct.reporting.frontier import generate_frontier_outputs
from lifluct.reporting.loader import load_run_directory
from lifluct.reporting.plots import (
    plot_attribution_mode_ranking_stability,
    plot_metric_heatmap,
    plot_metric_vs_parameter,
    plot_seed_variance_by_group,
)
from lifluct.reporting.tables import markdown_table, write_rows_csv
from lifluct.reporting.validation import validate_loaded_run
from lifluct.types import FailureModeObservation, RegimeConfig


def load_runs(run_dirs: Sequence[str | Path]) -> list[dict[str, Any]]:
    run_payloads: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        payload = load_run_directory(run_dir)
        warnings = payload.get("validation_warnings")
        failure_modes = payload.get("failure_modes")
        if warnings is None or failure_modes is None:
            warnings, failure_modes = validate_loaded_run(payload)
        payload["validation_warnings"] = warnings
        payload["failure_modes"] = failure_modes
        payload["run_dir"] = Path(run_dir)
        metadata_path = Path(run_dir) / "run_metadata.json"
        if metadata_path.exists():
            payload["metadata"] = json.loads(metadata_path.read_text(encoding="utf-8"))
        if "summary" in payload:
            payload["diagnostics"] = summarize_result_diagnostics(
                config=payload["config"],
                summary=payload["summary"],
                epoch_summaries=payload.get("epoch_summaries", []),
                cell_snapshots=payload.get("cell_snapshots", []),
                step_metrics=payload.get("step_metrics", []),
            )
        if payload.get("cell_snapshots") and payload.get("trades") and payload.get("step_metrics"):
            try:
                attribution_results = evaluate_attribution_modes(
                    config=payload["config"],
                    trades=payload["trades"],
                    step_metrics=payload["step_metrics"],
                    cell_snapshots=payload["cell_snapshots"],
                )
                payload["attribution_mode_results"] = attribution_results
                payload["attribution_ranking_stability"] = ranking_stability(attribution_results)
            except ValueError:
                payload["attribution_mode_results"] = {}
                payload["attribution_ranking_stability"] = []
        run_payloads.append(payload)
    return run_payloads


def comparison_rows(run_payloads: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in run_payloads:
        config = payload["config"]
        regime = RegimeConfig.from_run_config(config)
        summary = payload["summary"]
        epoch_summaries = payload.get("epoch_summaries", [])
        metadata = payload.get("metadata", {})
        warnings = payload.get("validation_warnings", [])
        failure_modes = payload.get("failure_modes", [])
        diagnostics = payload.get("diagnostics", {})
        stability_rows = payload.get("attribution_ranking_stability", [])
        mean_attribution_stability = (
            statistics.fmean(float(row["fitness_rank_correlation"]) for row in stability_rows)
            if stability_rows
            else 1.0
        )
        model_type = metadata.get("model_type", config.baseline_type)
        model_family = str(metadata.get("model_family") or _infer_model_family(config.lysis_mode))
        rows.append(
            {
                "label": metadata.get("label", Path(payload["run_dir"]).name),
                "suite_id": metadata.get("suite_id", ""),
                "experiment_family": metadata.get("experiment_family", ""),
                "evaluation_split": metadata.get("evaluation_split", ""),
                "model_type": model_type,
                "model_family": model_family,
                "retention_mode": metadata.get("retention_mode", "full_trace"),
                "baseline_type": config.baseline_type,
                "seed": config.seed,
                "regime_id": metadata.get("regime_id", regime.regime_id()),
                "sigma": config.sigma,
                "oracle_mode": config.oracle_mode,
                "oracle_lag_steps": config.oracle_lag_steps,
                "epoch_length": config.epoch_length,
                "num_steps": config.num_steps,
                "num_cells": config.num_cells,
                "omega": config.fitness_omega,
                "lambda": config.fitness_lambda,
                "gamma": config.fitness_gamma,
                "kappa": config.kappa,
                "attribution_mode": config.attribution_mode,
                "user_routing_mode": config.user_routing_mode,
                "toxic_mode": config.toxic_mode or config.toxic_routing_mode,
                "toxic_routing_mode": config.toxic_routing_mode,
                "fitness_mode": config.fitness_mode,
                "lysis_mode": config.lysis_mode,
                "mutation_sigma_mu": config.mutation_sigma_mu,
                "mutation_sigma_beta": config.mutation_sigma_beta,
                "lp_minus_hodl_b": summary.lp_minus_hodl_b,
                "total_attributed_loss_b": summary.total_attributed_loss_b,
                "total_lp_revenue_b": summary.total_lp_revenue_b,
                "total_trader_cost_b": summary.total_trader_cost_b,
                "total_arbitrage_profit_b": summary.total_arbitrage_profit_b,
                "active_cell_count": epoch_summaries[-1].num_active_cells if epoch_summaries else 1,
                "lysis_count": summary.total_lysis_count,
                "gene_dispersion_final": final_gene_dispersion(payload.get("cell_snapshots", [])),
                "top_cell_concentration_final": _last_diagnostic_value(
                    diagnostics.get("top_1_cell_volume_share_by_epoch", {}),
                ),
                "oscillation_score": float(diagnostics.get("oscillation_score", 0.0)),
                "dead_volume_score": float(diagnostics.get("dead_volume_score", 0.0)),
                "attribution_fitness_rank_stability": mean_attribution_stability,
                "warnings_count": len(warnings),
                "failure_modes_count": len(failure_modes),
                "failure_modes": "; ".join(mode.mode for mode in failure_modes) if failure_modes else "",
                "run_dir": str(payload["run_dir"]),
            }
        )
    return rows


def aggregate_rows(
    rows: Sequence[dict[str, Any]],
    *,
    group_by: Sequence[str],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in group_by)
        grouped[key].append(row)

    metric_fields = [
        "lp_minus_hodl_b",
        "total_attributed_loss_b",
        "total_lp_revenue_b",
        "total_trader_cost_b",
        "total_arbitrage_profit_b",
        "active_cell_count",
        "lysis_count",
        "gene_dispersion_final",
        "top_cell_concentration_final",
        "oscillation_score",
        "dead_volume_score",
        "attribution_fitness_rank_stability",
        "warnings_count",
        "failure_modes_count",
    ]
    aggregated: list[dict[str, Any]] = []
    for key, members in grouped.items():
        row: dict[str, Any] = {field: value for field, value in zip(group_by, key, strict=True)}
        row["num_runs"] = len(members)
        for field in metric_fields:
            values = [float(member[field]) for member in members]
            row[f"{field}_mean"] = statistics.fmean(values)
            row[f"{field}_std"] = statistics.pstdev(values) if len(values) > 1 else 0.0
        aggregated.append(row)
    return aggregated


def heuristic_failure_flags(run_payloads: Sequence[dict[str, Any]]) -> list[str]:
    counter: Counter[tuple[str, str]] = Counter()
    evidence: dict[tuple[str, str], str] = {}
    triggers: dict[tuple[str, str], str] = {}
    for payload in run_payloads:
        for mode in payload.get("failure_modes", []):
            if isinstance(mode, FailureModeObservation):
                key = (mode.mode, mode.severity)
                counter[key] += 1
                evidence.setdefault(key, mode.evidence)
                if mode.trigger_heuristic:
                    triggers.setdefault(key, mode.trigger_heuristic)
            else:
                key = (str(mode), "warning")
                counter[key] += 1
    rows = []
    for (mode_name, severity), count in counter.most_common():
        trigger = f" Trigger: {triggers[(mode_name, severity)]}." if (mode_name, severity) in triggers else ""
        example = f" Example evidence: {evidence[(mode_name, severity)]}." if (mode_name, severity) in evidence else ""
        rows.append(
            f"`{mode_name}` ({severity}, heuristic) in {count} run(s).{trigger}{example}"
        )
    return rows


def validation_warning_rows(run_payloads: Sequence[dict[str, Any]]) -> list[str]:
    rows: list[str] = []
    for payload in run_payloads:
        label = str(payload.get("metadata", {}).get("label", Path(payload["run_dir"]).name))
        split = str(payload.get("metadata", {}).get("evaluation_split", "")).strip()
        scoped_label = f"{split}:{label}" if split else label
        for warning in payload.get("validation_warnings", []):
            rows.append(f"`{scoped_label}` [{warning.severity}]: {warning.message}")
    return rows


def statistical_notes(rows: Sequence[dict[str, Any]], *, group_by: Sequence[str]) -> list[str]:
    aggregated = aggregate_rows(rows, group_by=group_by)
    notes: list[str] = []
    for group in aggregated:
        if group["num_runs"] < 3:
            label = ", ".join(f"{field}={group[field]}" for field in group_by)
            notes.append(
                f"Group `{label}` has only {group['num_runs']} run(s), so variance estimates are weak."
            )
    return notes


def collect_run_dirs_from_experiment(experiment_dir: str | Path) -> list[Path]:
    root = Path(experiment_dir)
    runs_root = root / "runs"
    if runs_root.exists():
        return sorted(
            path for path in runs_root.iterdir() if path.is_dir() and (path / "config_used.yaml").exists()
        )
    return sorted(
        path for path in root.iterdir() if path.is_dir() and (path / "config_used.yaml").exists()
    )


def key_observations(rows: Sequence[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No runs were available for comparison."]
    best_row = max(rows, key=lambda row: float(row["lp_minus_hodl_b"]))
    worst_row = min(rows, key=lambda row: float(row["lp_minus_hodl_b"]))
    highest_loss = max(rows, key=lambda row: float(row["total_attributed_loss_b"]))
    observations = [
        (
            f"Best LP-minus-HODL result: `{best_row['label']}` at "
            f"`{best_row['lp_minus_hodl_b']:.6f}`."
        ),
        (
            f"Worst LP-minus-HODL result: `{worst_row['label']}` at "
            f"`{worst_row['lp_minus_hodl_b']:.6f}`."
        ),
        (
            f"Highest attributed loss observed in `{highest_loss['label']}` at "
            f"`{highest_loss['total_attributed_loss_b']:.6f}`."
        ),
    ]
    families = {str(row.get("model_family", "")) for row in rows}
    if len(families) > 1:
        observations.append(
            "This comparison spans multiple model families; default tables are separated so lysis and no-lysis rows are not merged by accident."
        )
    model_types = {str(row.get("model_type", "")) for row in rows}
    if any(
        pair.issubset(model_types)
        for pair in [
            {"best_fixed_single_cell", "lifluct_multi_cell"},
            {"best_fixed_single_cell", "lifluct_multi_cell_no_lysis"},
            {"best_fixed_single_cell_with_lysis", "lifluct_multi_cell_with_lysis"},
        ]
    ):
        best_fixed_models = {"best_fixed_single_cell", "best_fixed_single_cell_with_lysis"}
        lifluct_models = {"lifluct_multi_cell", "lifluct_multi_cell_no_lysis", "lifluct_multi_cell_with_lysis"}
        best_fixed = statistics.fmean(
            float(row["lp_minus_hodl_b"]) for row in rows if row["model_type"] in best_fixed_models
        )
        lifluct = statistics.fmean(
            float(row["lp_minus_hodl_b"]) for row in rows if row["model_type"] in lifluct_models
        )
        relation = "outperformed" if lifluct > best_fixed else "underperformed"
        observations.append(
            f"LIFLUCT `{relation}` the best-fixed cohort on mean LP-minus-HODL (`{lifluct:.6f}` vs `{best_fixed:.6f}`)."
        )
    if any(float(row["lp_minus_hodl_b"]) < 0 for row in rows):
        observations.append(
            "At least one run underperformed HODL, so positive cases should not be treated as universal."
        )
    return observations


def weak_result_rows(rows: Sequence[dict[str, Any]]) -> list[str]:
    weak_rows = []
    for row in rows:
        if float(row["lp_minus_hodl_b"]) < 0 or int(row["failure_modes_count"]) > 0:
            weak_rows.append(
                (
                    f"`{row['label']}`: lp_minus_hodl_b=`{float(row['lp_minus_hodl_b']):.6f}`, "
                    f"heuristic_failure_flags=`{row['failure_modes'] or 'none'}`."
                )
            )
    return weak_rows


def attribution_robustness_rows(run_payloads: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in run_payloads:
        metadata = payload.get("metadata", {})
        label = metadata.get("label", Path(payload["run_dir"]).name)
        model_type = metadata.get("model_type", payload["config"].baseline_type)
        model_family = metadata.get("model_family") or _infer_model_family(payload["config"].lysis_mode)
        regime_id = metadata.get("regime_id", RegimeConfig.from_run_config(payload["config"]).regime_id())
        for stability_row in payload.get("attribution_ranking_stability", []):
            rows.append(
                {
                    "label": label,
                    "model_type": model_type,
                    "model_family": model_family,
                    "regime_id": regime_id,
                    "mode": stability_row["mode"],
                    "loss_rank_correlation": stability_row["loss_rank_correlation"],
                    "fitness_rank_correlation": stability_row["fitness_rank_correlation"],
                    "loss_pairwise_agreement": stability_row["loss_pairwise_agreement"],
                    "fitness_pairwise_agreement": stability_row["fitness_pairwise_agreement"],
                    "fitness_top_1_overlap": stability_row["fitness_top_1_overlap"],
                    "fitness_top_2_overlap": stability_row["fitness_top_2_overlap"],
                    "fitness_bottom_1_overlap": stability_row["fitness_bottom_1_overlap"],
                    "fitness_bottom_2_overlap": stability_row["fitness_bottom_2_overlap"],
                }
            )
    return rows


def aggregate_attribution_robustness(
    rows: Sequence[dict[str, Any]],
    *,
    group_by: Sequence[str] = ("mode",),
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in group_by)
        grouped[key].append(row)

    metrics = [
        "loss_rank_correlation",
        "fitness_rank_correlation",
        "loss_pairwise_agreement",
        "fitness_pairwise_agreement",
        "fitness_top_1_overlap",
        "fitness_top_2_overlap",
        "fitness_bottom_1_overlap",
        "fitness_bottom_2_overlap",
    ]
    aggregated: list[dict[str, Any]] = []
    for key, members in grouped.items():
        row: dict[str, Any] = {field: value for field, value in zip(group_by, key, strict=True)}
        row["num_runs"] = len(members)
        for metric in metrics:
            values = [float(member[metric]) for member in members]
            row[f"{metric}_mean"] = statistics.fmean(values)
        aggregated.append(row)
    return aggregated


def attribution_observations(rows: Sequence[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No attribution robustness analysis was available."]
    non_reference = [row for row in rows if row.get("mode") != "observed_spot"]
    if not non_reference:
        return ["Only the reference attribution mode was available."]
    weakest = min(non_reference, key=lambda row: float(row["fitness_rank_correlation_mean"]))
    strongest = max(non_reference, key=lambda row: float(row["fitness_rank_correlation_mean"]))
    observations = [
        (
            f"Most stable alternative fitness ranking was `{strongest['mode']}` with mean correlation "
            f"`{float(strongest['fitness_rank_correlation_mean']):.4f}`."
        ),
        (
            f"Least stable alternative fitness ranking was `{weakest['mode']}` with mean correlation "
            f"`{float(weakest['fitness_rank_correlation_mean']):.4f}`."
        ),
    ]
    if any(float(row["fitness_top_1_overlap_mean"]) < 1.0 for row in non_reference):
        observations.append("At least one attribution mode flipped the top-ranked Cell in some runs.")
    if any(float(row["fitness_bottom_1_overlap_mean"]) < 1.0 for row in non_reference):
        observations.append("At least one attribution mode flipped the bottom-ranked Cell in some runs.")
    return observations


def regime_definition_markdown(rows: Sequence[dict[str, Any]]) -> str:
    regimes = _unique_regime_rows(rows)
    if not regimes:
        return "_No regime metadata available._"
    if len(regimes) == 1:
        regime = regimes[0]
        bullets = [
            f"regime_id: `{regime['regime_id']}`",
            f"sigma: `{regime['sigma']}`",
            f"oracle_mode: `{regime['oracle_mode']}`",
            f"oracle_lag_steps: `{regime['oracle_lag_steps']}`",
            f"epoch_length: `{regime['epoch_length']}`",
            f"user_routing_mode: `{regime['user_routing_mode']}`",
            f"toxic_mode: `{regime['toxic_mode']}`",
            f"lysis_mode: `{regime['lysis_mode']}`",
            f"num_steps: `{regime['num_steps']}`",
            f"num_runs_in_report: `{regime['num_runs']}`",
        ]
        return "\n".join(f"- {item}" for item in bullets)
    return markdown_table(regimes)


def model_family_markdown(rows: Sequence[dict[str, Any]]) -> str:
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        grouped[str(row.get("model_family", "unknown"))].add(str(row.get("model_type", "unknown")))
    if not grouped:
        return "- None"
    lines = []
    for family, model_types in sorted(grouped.items()):
        lines.append(f"- `{family}`: {', '.join(f'`{model}`' for model in sorted(model_types))}")
    return "\n".join(lines)


def generate_comparison_outputs(
    run_payloads: Sequence[dict[str, Any]],
    *,
    output_dir: str | Path,
    group_by: Sequence[str],
) -> dict[str, Any]:
    output_root = Path(output_dir)
    plots_dir = output_root / DEFAULT_PLOTS_DIRNAME
    plots_dir.mkdir(parents=True, exist_ok=True)

    rows = comparison_rows(run_payloads)
    aggregated = aggregate_rows(rows, group_by=group_by)
    attribution_rows = attribution_robustness_rows(run_payloads)
    attribution_aggregates = aggregate_attribution_robustness(attribution_rows)

    write_rows_csv(output_root / "comparison_rows.csv", rows)
    write_rows_csv(output_root / "comparison_aggregates.csv", aggregated)
    write_rows_csv(output_root / "attribution_robustness_rows.csv", attribution_rows)
    write_rows_csv(output_root / "attribution_robustness_aggregates.csv", attribution_aggregates)

    plot_paths = generate_comparison_plots(rows, plots_dir)
    if attribution_aggregates:
        plot_paths["attribution_mode_ranking_stability"] = plot_attribution_mode_ranking_stability(
            [
                {
                    "mode": row["mode"],
                    "loss_rank_correlation": row["loss_rank_correlation_mean"],
                    "fitness_rank_correlation": row["fitness_rank_correlation_mean"],
                }
                for row in attribution_aggregates
            ],
            plots_dir / PLOT_FILE_NAMES["attribution_mode_ranking_stability"],
        )
    frontier_outputs = generate_frontier_outputs(rows, output_dir=output_root)
    plot_paths.update(frontier_outputs["plot_paths"])
    return {
        "rows": rows,
        "aggregated": aggregated,
        "comparison_table": _family_scoped_table(rows),
        "aggregated_table": _family_scoped_aggregate_table(rows, group_by=group_by),
        "frontier_table": frontier_outputs["frontier_table"],
        "frontier_observations": frontier_outputs["observations"],
        "heuristic_failure_flags": heuristic_failure_flags(run_payloads),
        "validation_warnings": validation_warning_rows(run_payloads),
        "statistical_notes": statistical_notes(rows, group_by=group_by),
        "key_observations": key_observations(rows),
        "weak_results": weak_result_rows(rows),
        "plot_paths": plot_paths,
        "regime_definition_block": regime_definition_markdown(rows),
        "model_family_block": model_family_markdown(rows),
        "attribution_robustness_table": markdown_table(attribution_aggregates),
        "attribution_robustness_rows": attribution_rows,
        "attribution_robustness_observations": attribution_observations(attribution_aggregates),
    }


def generate_comparison_plots(
    rows: Sequence[dict[str, Any]],
    output_dir: str | Path,
) -> dict[str, Path]:
    plots_dir = Path(output_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_paths: dict[str, Path] = {}

    if _has_variation(rows, "omega"):
        plot_paths["lp_minus_hodl_vs_omega"] = plot_metric_vs_parameter(
            rows,
            parameter_key="omega",
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["lp_minus_hodl_vs_omega"],
            title="LP Minus HODL Vs Omega",
        )
    if _has_variation(rows, "sigma"):
        plot_paths["lp_minus_hodl_vs_sigma"] = plot_metric_vs_parameter(
            rows,
            parameter_key="sigma",
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["lp_minus_hodl_vs_sigma"],
            title="LP Minus HODL Vs Sigma",
        )
    if _has_variation(rows, "oracle_lag_steps"):
        plot_paths["lp_minus_hodl_vs_oracle_lag"] = plot_metric_vs_parameter(
            rows,
            parameter_key="oracle_lag_steps",
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["lp_minus_hodl_vs_oracle_lag"],
            title="LP Minus HODL Vs Oracle Lag",
        )
    if _has_variation(rows, "omega") and _has_variation(rows, "sigma"):
        plot_paths["lp_outcome_heatmap_omega_sigma"] = plot_metric_heatmap(
            rows,
            x_key="omega",
            y_key="sigma",
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["lp_outcome_heatmap_omega_sigma"],
            title="LP Outcome Across (Omega, Sigma)",
        )
    if _has_variation(rows, "oracle_lag_steps") and _has_variation(rows, "kappa"):
        plot_paths["lp_outcome_heatmap_oracle_lag_kappa"] = plot_metric_heatmap(
            rows,
            x_key="oracle_lag_steps",
            y_key="kappa",
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["lp_outcome_heatmap_oracle_lag_kappa"],
            title="LP Outcome Across (Oracle Lag, Kappa)",
        )
    if _has_multiple_seeds(rows):
        group_key = "model_type" if _has_variation(rows, "model_type") else "label"
        plot_paths["seed_variance_lp_minus_hodl"] = plot_seed_variance_by_group(
            rows,
            group_key=group_key,
            metric_key="lp_minus_hodl_b",
            output_path=plots_dir / PLOT_FILE_NAMES["seed_variance_lp_minus_hodl"],
            title="LP Minus HODL Variance Across Seeds",
        )
    return plot_paths


def _family_scoped_table(rows: Sequence[dict[str, Any]]) -> str:
    if not rows:
        return "_No rows._"
    blocks: list[str] = []
    for family in sorted({str(row.get("model_family", "unknown")) for row in rows}):
        family_rows = [row for row in rows if str(row.get("model_family")) == family]
        blocks.append(f"### Family: `{family}`")
        blocks.append(
            markdown_table(
                family_rows,
                columns=[
                    "label",
                    "evaluation_split",
                    "model_type",
                    "seed",
                    "regime_id",
                    "lp_minus_hodl_b",
                    "total_attributed_loss_b",
                    "total_lp_revenue_b",
                    "total_trader_cost_b",
                    "lysis_count",
                    "gene_dispersion_final",
                    "attribution_fitness_rank_stability",
                ],
            )
        )
    return "\n\n".join(blocks)


def _family_scoped_aggregate_table(
    rows: Sequence[dict[str, Any]],
    *,
    group_by: Sequence[str],
) -> str:
    if not rows:
        return "_No rows._"
    blocks: list[str] = []
    for family in sorted({str(row.get("model_family", "unknown")) for row in rows}):
        family_rows = [row for row in rows if str(row.get("model_family")) == family]
        blocks.append(f"### Family: `{family}`")
        blocks.append(markdown_table(aggregate_rows(family_rows, group_by=group_by)))
    return "\n\n".join(blocks)


def _unique_regime_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        regime_id = str(row.get("regime_id", ""))
        regime_row = grouped.setdefault(
            regime_id,
            {
                "regime_id": regime_id,
                "sigma": row.get("sigma"),
                "oracle_mode": row.get("oracle_mode"),
                "oracle_lag_steps": row.get("oracle_lag_steps"),
                "epoch_length": row.get("epoch_length"),
                "user_routing_mode": row.get("user_routing_mode"),
                "toxic_mode": row.get("toxic_mode"),
                "lysis_mode": row.get("lysis_mode"),
                "num_steps": row.get("num_steps"),
                "num_runs": 0,
            },
        )
        regime_row["num_runs"] = int(regime_row["num_runs"]) + 1
    return list(grouped.values())


def _infer_model_family(lysis_mode: str) -> str:
    return "no_lysis" if lysis_mode == "off" else "lysis_enabled"


def _has_variation(rows: Sequence[dict[str, Any]], key: str) -> bool:
    return len({row.get(key) for row in rows}) > 1


def _has_multiple_seeds(rows: Sequence[dict[str, Any]]) -> bool:
    return len({row.get("seed") for row in rows}) > 1


def _last_diagnostic_value(diagnostic_map: Any) -> float:
    if not diagnostic_map:
        return 0.0
    if isinstance(diagnostic_map, dict):
        key = max(int(key) for key in diagnostic_map)
        return float(diagnostic_map[str(key)] if str(key) in diagnostic_map else diagnostic_map[key])
    return 0.0
