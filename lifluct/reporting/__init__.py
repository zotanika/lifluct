"""Reporting helpers for LIFLUCT runs."""

from lifluct.reporting.aggregate_stats import aggregate_result_rows
from lifluct.reporting.adjudication import adjudicate_family
from lifluct.reporting.bootstrap import bootstrap_confidence_interval
from lifluct.reporting.compare import generate_comparison_outputs, load_runs
from lifluct.reporting.experiment_registry import append_registry_records, upsert_registry_records, write_registry
from lifluct.reporting.frontier import generate_frontier_outputs
from lifluct.reporting.loader import load_run_directory
from lifluct.reporting.plots import generate_all_plots
from lifluct.reporting.prevalence import failure_flag_prevalence
from lifluct.reporting.regime_reports import (
    write_adjudication_master_markdown,
    write_prevalence_report_markdown,
    write_regime_family_report_markdown,
)
from lifluct.reporting.research_report import (
    write_attribution_robustness_report_markdown,
    write_best_fixed_train_test_report_markdown,
    write_frontier_report_markdown,
    write_thesis_adjudication_report_markdown,
)
from lifluct.reporting.summary import (
    write_comparison_report_markdown,
    write_failure_report_markdown,
    write_run_summary_markdown,
)
from lifluct.reporting.validation import validate_loaded_run, validate_result

__all__ = [
    "aggregate_result_rows",
    "adjudicate_family",
    "append_registry_records",
    "bootstrap_confidence_interval",
    "failure_flag_prevalence",
    "generate_all_plots",
    "generate_comparison_outputs",
    "generate_frontier_outputs",
    "load_run_directory",
    "load_runs",
    "upsert_registry_records",
    "validate_loaded_run",
    "validate_result",
    "write_adjudication_master_markdown",
    "write_attribution_robustness_report_markdown",
    "write_best_fixed_train_test_report_markdown",
    "write_comparison_report_markdown",
    "write_failure_report_markdown",
    "write_frontier_report_markdown",
    "write_prevalence_report_markdown",
    "write_regime_family_report_markdown",
    "write_registry",
    "write_run_summary_markdown",
    "write_thesis_adjudication_report_markdown",
]
