"""Run a simple parameter sweep over Phase 1 configs."""

from __future__ import annotations

import argparse
import csv
import itertools
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from lifluct.cli.run_simulation import execute_and_write_run
from lifluct.constants import DEFAULT_OUTPUT_DIR
from lifluct.reporting.loader import load_run_config
from lifluct.types import RunConfig


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("sweep", help=__doc__)
    parser.add_argument("--config", required=True, help="Path to a sweep YAML config")
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Defaults to runs/sweep_<timestamp>",
    )
    parser.set_defaults(func=_run)


def _run(args) -> None:
    sweep_config_path = Path(args.config)
    with sweep_config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    base_config = _load_base_config(raw, sweep_config_path.parent)
    sweep_spec = raw.get("sweep", {})
    output_root = Path(args.output_dir) if args.output_dir else _default_sweep_output_dir()
    output_root.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, Any]] = []
    keys = sorted(sweep_spec.keys())
    values_product = itertools.product(*(sweep_spec[key] for key in keys))
    for index, values in enumerate(values_product):
        overrides = dict(zip(keys, values, strict=True))
        run_config = replace(base_config, **overrides)
        run_dir = output_root / f"run_{index:03d}"
        result = execute_and_write_run(run_config, run_dir)
        summary_rows.append(
            {
                "run_dir": str(run_dir),
                **overrides,
                **result.summary.to_dict(),
            }
        )

    _write_summary_rows(output_root / "sweep_results.csv", summary_rows)
    print(output_root)


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to a sweep YAML config")
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Defaults to runs/sweep_<timestamp>",
    )
    args = parser.parse_args()
    _run(args)


def _load_base_config(raw: dict[str, Any], config_dir: Path) -> RunConfig:
    base_config = raw.get("base_config")
    if isinstance(base_config, str):
        return load_run_config(config_dir / base_config)
    if isinstance(base_config, dict):
        return RunConfig.from_mapping(base_config)
    raise ValueError("sweep config must provide a base_config path or mapping")


def _write_summary_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _default_sweep_output_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(DEFAULT_OUTPUT_DIR) / f"sweep_{timestamp}"


if __name__ == "__main__":
    main()
