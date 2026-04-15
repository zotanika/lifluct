"""Run one Phase 4.2 regime family with shard/resume/retention controls."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from lifluct.core.cell import CellGenes
from lifluct.orchestration.manifest import build_run_manifest, load_family_manifest, write_manifest
from lifluct.orchestration.scheduler import run_manifest_entries
from lifluct.orchestration.shard import shard_entries
from lifluct.reporting.loader import load_run_config


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("family", help=__doc__)
    parser.add_argument("--family-config", required=True, help="Path to a regime-family YAML")
    parser.add_argument("--output-dir", help="Optional family output directory")
    parser.add_argument("--models", nargs="+", help="Optional model subset")
    parser.add_argument("--seed-override", type=int, help="Optional fixed seed override")
    parser.add_argument("--retention-mode", help="Optional retention override")
    parser.add_argument("--best-fixed-config", help="Optional best-fixed candidate config")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--resume", action="store_true", help="Resume by skipping or recovering completed runs")
    parser.add_argument("--shard-index", type=int, default=0, help="Zero-based shard index")
    parser.add_argument("--shard-count", type=int, default=1, help="Total number of shards")
    parser.add_argument("--no-aggregate", action="store_true", help="Skip post-run aggregation")
    parser.set_defaults(func=_run)


def _run(args) -> None:
    run_family_workflow(
        family_config_path=Path(args.family_config),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        models_subset=args.models,
        seed_override=args.seed_override,
        retention_override=args.retention_mode,
        best_fixed_config=args.best_fixed_config,
        workers=args.workers,
        resume=args.resume,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        aggregate_after=not args.no_aggregate,
    )


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-config", required=True, help="Path to a regime-family YAML")
    parser.add_argument("--output-dir", help="Optional family output directory")
    parser.add_argument("--models", nargs="+", help="Optional model subset")
    parser.add_argument("--seed-override", type=int, help="Optional fixed seed override")
    parser.add_argument("--retention-mode", help="Optional retention override")
    parser.add_argument("--best-fixed-config", help="Optional best-fixed candidate config")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--resume", action="store_true", help="Resume by skipping or recovering completed runs")
    parser.add_argument("--shard-index", type=int, default=0, help="Zero-based shard index")
    parser.add_argument("--shard-count", type=int, default=1, help="Total number of shards")
    parser.add_argument("--no-aggregate", action="store_true", help="Skip post-run aggregation")
    args = parser.parse_args()
    _run(args)


def run_family_workflow(
    *,
    family_config_path: Path,
    output_dir: Path | None,
    models_subset: Sequence[str] | None,
    seed_override: int | None,
    retention_override: str | None,
    best_fixed_config: str | None,
    workers: int,
    resume: bool,
    shard_index: int,
    shard_count: int,
    aggregate_after: bool,
) -> Path:
    family = load_family_manifest(family_config_path)
    family_dir = output_dir or Path("runs") / "phase42" / family.family_name
    family_dir.mkdir(parents=True, exist_ok=True)
    (family_dir / "family_config.yaml").write_text(
        family_config_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    best_fixed_genes = _load_best_fixed_genes(best_fixed_config)
    manifest_entries = build_run_manifest(
        family,
        output_root=family_dir,
        models_subset=models_subset,
        seed_override=seed_override,
        retention_override=retention_override,
        best_fixed_genes=best_fixed_genes,
    )
    write_manifest(family_dir / "manifest.csv", manifest_entries)
    shard_manifest = shard_entries(
        manifest_entries,
        shard_index=shard_index,
        shard_count=shard_count,
    )
    if shard_count > 1:
        write_manifest(
            family_dir / f"manifest_shard_{shard_index:02d}_of_{shard_count:02d}.csv",
            shard_manifest,
        )
    run_manifest_entries(
        shard_manifest,
        family_dir=family_dir,
        max_workers=workers,
        resume=resume,
        shard_index=shard_index,
        shard_count=shard_count,
    )
    if aggregate_after and shard_count == 1:
        from lifluct.cli.aggregate_results import aggregate_family_directory

        aggregate_family_directory(family_dir)
    print(family_dir)
    return family_dir


def _load_best_fixed_genes(path: str | None) -> CellGenes | None:
    if not path:
        return None
    config = load_run_config(path)
    return CellGenes(f_min=config.f_min, mu=config.mu, tau=config.tau, beta=config.beta)


if __name__ == "__main__":
    main()
