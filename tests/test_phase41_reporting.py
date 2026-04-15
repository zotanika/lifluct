from lifluct.reporting.research_report import (
    write_attribution_robustness_report_markdown,
    write_best_fixed_train_test_report_markdown,
)
from lifluct.reporting.summary import write_comparison_report_markdown
from lifluct.reporting.tables import markdown_table


def test_markdown_table_escapes_pipe_characters() -> None:
    table = markdown_table([{"label": "alpha | beta", "value": 1.0}])

    assert "alpha \\| beta" in table


def test_best_fixed_train_test_report_mentions_budget_and_splits(tmp_path) -> None:
    output = tmp_path / "best_fixed_train_test_report.md"
    write_best_fixed_train_test_report_markdown(
        output,
        title="Best Fixed",
        search_method="random_search",
        search_profile="serious",
        search_budget=128,
        objective_mode="lp_minus_hodl",
        aggregate_mode="mean",
        family="no_lysis",
        best_gene_block="| f_min |\n| --- |\n| 0.003 |",
        in_sample_block="train rows",
        out_of_sample_block="test rows",
    )

    content = output.read_text(encoding="utf-8")
    assert "search_budget: `128`" in content
    assert "aggregate_mode: `mean`" in content
    assert "In-Sample Results" in content
    assert "Out-Of-Sample Results" in content


def test_attribution_robustness_report_includes_rank_stability_metrics(tmp_path) -> None:
    output = tmp_path / "attribution_robustness_report.md"
    write_attribution_robustness_report_markdown(
        output,
        title="Attribution Robustness",
        regime_definition_block="- regime_id: `regime_demo`",
        model_family_block="- `no_lysis`",
        robustness_table=(
            "| mode | fitness_rank_correlation_mean | fitness_top_1_overlap_mean |\n"
            "| --- | --- | --- |\n"
            "| twap | 0.7500 | 1.0000 |"
        ),
        observations=["Top-ranked Cell stayed stable in this toy example."],
        plot_paths={},
    )

    content = output.read_text(encoding="utf-8")
    assert "fitness_rank_correlation_mean" in content
    assert "fitness_top_1_overlap_mean" in content


def test_comparison_report_uses_relative_plot_paths(tmp_path) -> None:
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    plots_dir = report_dir / "plots"
    plots_dir.mkdir()
    plot_path = plots_dir / "frontier.png"
    plot_path.write_text("placeholder\n", encoding="utf-8")

    output = report_dir / "comparison_report.md"
    write_comparison_report_markdown(
        output,
        title="Comparison",
        regime_definition_block="- regime_id: `regime_demo`",
        model_family_block="- `no_lysis`",
        comparison_table="| label |\n| --- |\n| demo |",
        aggregated_table="| label |\n| --- |\n| demo |",
        heuristic_failure_flags=["`dead_volume_equilibrium` (warning, heuristic)"],
        validation_warnings=["[warning] toy warning"],
        statistical_notes=["Small sample size."],
        plot_paths={"frontier": plot_path},
        key_observations=["Toy observation."],
        attribution_robustness_block="| mode |\n| --- |\n| observed_spot |",
    )

    content = output.read_text(encoding="utf-8")
    assert str(tmp_path) not in content
    assert "plots/frontier.png" in content or "../frontier.png" in content or "frontier.png" in content
