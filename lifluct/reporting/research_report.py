"""Markdown research-report writers for Phase 4 adjudication workflows."""

from __future__ import annotations

import statistics
from pathlib import Path
from string import Template
from typing import Any, Sequence

from lifluct.reporting.tables import bullet_list


def write_frontier_report_markdown(
    output_path: str | Path,
    *,
    title: str,
    regime_definition_block: str,
    model_family_block: str,
    frontier_table: str,
    observations: Sequence[str],
    plot_paths: dict[str, Path],
) -> Path:
    template = _load_template("frontier_report_template.md")
    output = Path(output_path)
    report_dir = output.parent
    rendered = template.safe_substitute(
        title=title,
        regime_definition_block=regime_definition_block,
        model_family_block=model_family_block,
        frontier_table=frontier_table,
        observations_block=bullet_list(list(observations)),
        plots_block=bullet_list(
            [f"`{name}`: `{_relative_display_path(path, report_dir)}`" for name, path in plot_paths.items()]
        ),
    )
    output.write_text(rendered, encoding="utf-8")
    return output


def write_thesis_adjudication_report_markdown(
    output_path: str | Path,
    *,
    title: str,
    regime_definition_block: str,
    model_family_block: str,
    rows: Sequence[dict[str, Any]],
    frontier_observations: Sequence[str],
    heuristic_failure_flags: Sequence[str],
    validation_warnings: Sequence[str],
    statistical_notes: Sequence[str],
    attribution_robustness_block: str,
    plot_paths: dict[str, Path],
) -> Path:
    template = _load_template("thesis_adjudication_template.md")
    output = Path(output_path)
    report_dir = output.parent
    mixed_families = _has_family(rows, "lysis_enabled") and _has_family(rows, "no_lysis")
    family_note = (
        "This report spans multiple model families. Read the family-separated comparison tables first; a single headline comparison would be misleading."
        if mixed_families
        else None
    )
    rendered = template.safe_substitute(
        title=title,
        regime_definition_block=regime_definition_block,
        model_family_block=model_family_block,
        did_lifluct_beat_static=family_note or _comparison_answer(rows, "lifluct_multi_cell_no_lysis", "static_cpmm"),
        did_lifluct_beat_dynamic=family_note or _comparison_answer(
            rows,
            "lifluct_multi_cell_with_lysis" if _has_family(rows, "lysis_enabled") and not _has_family(rows, "no_lysis") else "lifluct_multi_cell_no_lysis",
            "dynamic_fee_single_with_lysis" if _has_family(rows, "lysis_enabled") and not _has_family(rows, "no_lysis") else "dynamic_fee_single",
        ),
        did_lifluct_beat_best_fixed=family_note or _comparison_answer(
            rows,
            "lifluct_multi_cell_with_lysis" if _has_family(rows, "lysis_enabled") and not _has_family(rows, "no_lysis") else "lifluct_multi_cell_no_lysis",
            "best_fixed_single_cell_with_lysis" if _has_family(rows, "lysis_enabled") and not _has_family(rows, "no_lysis") else "best_fixed_single_cell",
        ),
        lp_vs_trader_tradeoff=_lp_vs_trader_answer(rows),
        oracle_sensitivity=_oracle_answer(rows),
        adversary_sensitivity=_adversary_answer(rows),
        attribution_robustness_block=attribution_robustness_block,
        heuristic_failure_flags_block=bullet_list(list(heuristic_failure_flags)),
        validation_warnings_block=bullet_list(list(validation_warnings)),
        frontier_observations_block=bullet_list(list(frontier_observations)),
        statistical_notes_block=bullet_list(list(statistical_notes)),
        plots_block=bullet_list(
            [f"`{name}`: `{_relative_display_path(path, report_dir)}`" for name, path in plot_paths.items()]
        ),
    )
    output.write_text(rendered, encoding="utf-8")
    return output


def write_attribution_robustness_report_markdown(
    output_path: str | Path,
    *,
    title: str,
    regime_definition_block: str,
    model_family_block: str,
    robustness_table: str,
    observations: Sequence[str],
    plot_paths: dict[str, Path],
) -> Path:
    output = Path(output_path)
    report_dir = output.parent
    lines = [
        f"# {title}",
        "",
        "## Regime Definition",
        "",
        regime_definition_block,
        "",
        "## Model Family",
        "",
        model_family_block,
        "",
        "## Attribution Robustness",
        "",
        robustness_table,
        "",
        "## Observations",
        "",
        bullet_list(list(observations)),
        "",
        "## Related Plots",
        "",
        bullet_list(
            [f"`{name}`: `{_relative_display_path(path, report_dir)}`" for name, path in plot_paths.items()]
        ),
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def write_best_fixed_train_test_report_markdown(
    output_path: str | Path,
    *,
    title: str,
    search_method: str,
    search_profile: str,
    search_budget: int,
    objective_mode: str,
    aggregate_mode: str,
    family: str,
    best_gene_block: str,
    in_sample_block: str,
    out_of_sample_block: str,
) -> Path:
    output = Path(output_path)
    lines = [
        f"# {title}",
        "",
        "## Search Setup",
        "",
        bullet_list(
            [
                f"search_method: `{search_method}`",
                f"search_profile: `{search_profile}`",
                f"search_budget: `{search_budget}`",
                f"objective_mode: `{objective_mode}`",
                f"aggregate_mode: `{aggregate_mode}`",
                f"comparison_family: `{family}`",
            ]
        ),
        "",
        "## Best Gene Vector",
        "",
        best_gene_block,
        "",
        "## In-Sample Results",
        "",
        in_sample_block,
        "",
        "## Out-Of-Sample Results",
        "",
        out_of_sample_block,
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _comparison_answer(
    rows: Sequence[dict[str, Any]],
    contender: str,
    baseline: str,
) -> str:
    contender_mean = _mean_metric(rows, contender, "lp_minus_hodl_b")
    baseline_mean = _mean_metric(rows, baseline, "lp_minus_hodl_b")
    if contender_mean is None or baseline_mean is None:
        return f"Insufficient runs to compare `{contender}` against `{baseline}`."
    relation = "outperformed" if contender_mean > baseline_mean else "underperformed"
    return (
        f"On the available sample, `{contender}` {relation} `{baseline}` on mean LP-minus-HODL "
        f"(`{contender_mean:.6f}` vs `{baseline_mean:.6f}`), but this is not proof of general superiority."
    )


def _lp_vs_trader_answer(rows: Sequence[dict[str, Any]]) -> str:
    lifluct_model = _preferred_lifluct_model(rows)
    dynamic_model = _preferred_dynamic_model(rows)
    lifluct_lp = _mean_metric(rows, lifluct_model, "lp_minus_hodl_b")
    dynamic_lp = _mean_metric(rows, dynamic_model, "lp_minus_hodl_b")
    lifluct_cost = _mean_metric(rows, lifluct_model, "total_trader_cost_b")
    dynamic_cost = _mean_metric(rows, dynamic_model, "total_trader_cost_b")
    if None in {lifluct_lp, dynamic_lp, lifluct_cost, dynamic_cost}:
        return "Insufficient runs to summarize the LP-versus-trader frontier."
    return (
        f"LIFLUCT mean LP-minus-HODL was `{lifluct_lp:.6f}` versus dynamic baseline `{dynamic_lp:.6f}`, "
        f"while mean trader cost was `{lifluct_cost:.6f}` versus `{dynamic_cost:.6f}`. "
        "Treat any LP gain that arrives with materially higher trader cost as a tradeoff, not a free lunch."
    )


def _oracle_answer(rows: Sequence[dict[str, Any]]) -> str:
    lagged_rows = [row for row in rows if float(row.get("oracle_lag_steps", 0)) > 0]
    if not lagged_rows:
        return "No oracle-lag regimes were present in this report."
    lagged_mean = statistics.fmean(float(row["lp_minus_hodl_b"]) for row in lagged_rows)
    return (
        f"Under lagged-oracle regimes in this sample, mean LP-minus-HODL was `{lagged_mean:.6f}`. "
        "If that turns sharply negative under small lag, the mechanism should be considered oracle-fragile."
    )


def _adversary_answer(rows: Sequence[dict[str, Any]]) -> str:
    toxic_modes = sorted(
        {str(row.get("toxic_mode", "")) for row in rows if row.get("toxic_mode") is not None}
    )
    if len(toxic_modes) <= 1:
        return "No multi-adversary comparison was present in this report."
    return (
        f"This report includes multiple toxic modes: `{', '.join(toxic_modes)}`. "
        "Any result that survives only the weakest adversary should be treated cautiously."
    )


def _mean_metric(rows: Sequence[dict[str, Any]], model_type: str, metric_key: str) -> float | None:
    values = [
        float(row[metric_key])
        for row in rows
        if _model_matches(str(row.get("model_type", row.get("baseline_type"))), model_type)
        and row.get(metric_key) is not None
    ]
    if not values:
        return None
    return statistics.fmean(values)


def _preferred_lifluct_model(rows: Sequence[dict[str, Any]]) -> str:
    if _has_family(rows, "lysis_enabled") and not _has_family(rows, "no_lysis"):
        return "lifluct_multi_cell_with_lysis"
    return "lifluct_multi_cell_no_lysis"


def _preferred_dynamic_model(rows: Sequence[dict[str, Any]]) -> str:
    if _has_family(rows, "lysis_enabled") and not _has_family(rows, "no_lysis"):
        return "dynamic_fee_single_with_lysis"
    return "dynamic_fee_single"


def _has_family(rows: Sequence[dict[str, Any]], family: str) -> bool:
    return any(str(row.get("model_family")) == family for row in rows)


def _model_matches(actual: str, target: str) -> bool:
    aliases = {
        "lifluct_multi_cell_no_lysis": {"lifluct_multi_cell_no_lysis", "lifluct_multi_cell"},
        "dynamic_fee_single": {"dynamic_fee_single"},
        "best_fixed_single_cell": {"best_fixed_single_cell"},
        "lifluct_multi_cell_with_lysis": {"lifluct_multi_cell_with_lysis"},
        "dynamic_fee_single_with_lysis": {"dynamic_fee_single_with_lysis"},
        "best_fixed_single_cell_with_lysis": {"best_fixed_single_cell_with_lysis"},
        "static_cpmm": {"static_cpmm"},
    }
    return actual in aliases.get(target, {target})


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
