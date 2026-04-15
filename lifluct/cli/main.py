"""LIFLUCT -- policy evaluation toolkit for automated market makers."""

from __future__ import annotations

import argparse
import sys

from lifluct.cli import (
    aggregate_results,
    compare_runs,
    export_report_bundle,
    make_adjudication_report,
    make_report,
    resume_batch,
    run_best_fixed_search,
    run_experiment_grid,
    run_large_grid,
    run_regime_family,
    run_sharded_batch,
    run_simulation,
    run_sweep,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lifluct",
        description=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    run_simulation.build_parser(sub)
    run_sweep.build_parser(sub)
    make_report.build_parser(sub)
    run_experiment_grid.build_parser(sub)
    compare_runs.build_parser(sub)
    export_report_bundle.build_parser(sub)
    run_best_fixed_search.build_parser(sub)
    run_regime_family.build_parser(sub)
    run_large_grid.build_parser(sub)
    run_sharded_batch.build_parser(sub)
    resume_batch.build_parser(sub)
    aggregate_results.build_parser(sub)
    make_adjudication_report.build_parser(sub)

    # MCP server subcommand
    try:
        from lifluct.plugin import cli as mcp_cli
        mcp_cli.build_parser(sub)
    except ImportError:
        pass

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
