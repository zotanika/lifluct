"""Copy selected run and comparison artifacts into one report bundle directory."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from lifluct.constants import DEFAULT_OUTPUT_DIR


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("bundle", help=__doc__)
    parser.add_argument("--run-dir", action="append", default=[], help="Run directory to include")
    parser.add_argument("--comparison-dir", action="append", default=[], help="Comparison directory to include")
    parser.add_argument("--experiment-dir", action="append", default=[], help="Experiment directory to include")
    parser.add_argument("--output-dir", help="Bundle output directory")
    parser.set_defaults(func=_run)


def _run(args) -> None:
    output_dir = Path(args.output_dir) if args.output_dir else Path(DEFAULT_OUTPUT_DIR) / f"report_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "runs").mkdir(exist_ok=True)
    (output_dir / "comparisons").mkdir(exist_ok=True)
    (output_dir / "experiments").mkdir(exist_ok=True)

    for run_dir in args.run_dir:
        _copy_tree(Path(run_dir), output_dir / "runs" / Path(run_dir).name)
    for comparison_dir in args.comparison_dir:
        _copy_tree(Path(comparison_dir), output_dir / "comparisons" / Path(comparison_dir).name)
    for experiment_dir in args.experiment_dir:
        _copy_tree(Path(experiment_dir), output_dir / "experiments" / Path(experiment_dir).name)

    run_lines = [f"- `{Path(path).name}`" for path in args.run_dir] or ["- None"]
    comparison_lines = [f"- `{Path(path).name}`" for path in args.comparison_dir] or ["- None"]
    experiment_lines = [f"- `{Path(path).name}`" for path in args.experiment_dir] or ["- None"]

    index_lines = [
        "# Report Bundle",
        "",
        "## Included Run Directories",
        "",
        *run_lines,
        "",
        "## Included Comparison Directories",
        "",
        *comparison_lines,
        "",
        "## Included Experiment Directories",
        "",
        *experiment_lines,
    ]
    (output_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(output_dir)


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", action="append", default=[], help="Run directory to include")
    parser.add_argument("--comparison-dir", action="append", default=[], help="Comparison directory to include")
    parser.add_argument("--experiment-dir", action="append", default=[], help="Experiment directory to include")
    parser.add_argument("--output-dir", help="Bundle output directory")
    args = parser.parse_args()
    _run(args)


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


if __name__ == "__main__":
    main()
