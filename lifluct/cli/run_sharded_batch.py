"""Run one shard of a Phase 4.2 family batch."""

from __future__ import annotations

import argparse
from pathlib import Path

from lifluct.cli.run_regime_family import run_family_workflow
from lifluct.orchestration.manifest import load_manifest_entries
from lifluct.orchestration.scheduler import run_manifest_entries
from lifluct.orchestration.shard import shard_entries


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("sharded", help=__doc__)
    parser.add_argument("--family-config", help="Path to a regime-family YAML")
    parser.add_argument("--manifest", help="Optional manifest CSV to shard directly")
    parser.add_argument("--output-dir", help="Optional family output directory")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--resume", action="store_true", help="Resume by skipping completed runs")
    parser.add_argument("--shard-index", type=int, required=True, help="Zero-based shard index")
    parser.add_argument("--shard-count", type=int, required=True, help="Total shard count")
    parser.add_argument("--retention-mode", help="Optional retention override")
    parser.add_argument("--best-fixed-config", help="Optional best-fixed candidate config")
    parser.set_defaults(func=_run)


def _run(args) -> None:
    if args.manifest:
        manifest_path = Path(args.manifest)
        family_dir = Path(args.output_dir) if args.output_dir else manifest_path.parent
        entries = load_manifest_entries(manifest_path)
        sharded = shard_entries(entries, shard_index=args.shard_index, shard_count=args.shard_count)
        run_manifest_entries(
            sharded,
            family_dir=family_dir,
            max_workers=args.workers,
            resume=args.resume,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
        )
        print(family_dir)
        return
    if not args.family_config:
        raise ValueError("either --family-config or --manifest is required")
    run_family_workflow(
        family_config_path=Path(args.family_config),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        models_subset=None,
        seed_override=None,
        retention_override=args.retention_mode,
        best_fixed_config=args.best_fixed_config,
        workers=args.workers,
        resume=args.resume,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        aggregate_after=False,
    )


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-config", help="Path to a regime-family YAML")
    parser.add_argument("--manifest", help="Optional manifest CSV to shard directly")
    parser.add_argument("--output-dir", help="Optional family output directory")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--resume", action="store_true", help="Resume by skipping completed runs")
    parser.add_argument("--shard-index", type=int, required=True, help="Zero-based shard index")
    parser.add_argument("--shard-count", type=int, required=True, help="Total shard count")
    parser.add_argument("--retention-mode", help="Optional retention override")
    parser.add_argument("--best-fixed-config", help="Optional best-fixed candidate config")
    args = parser.parse_args()
    _run(args)


if __name__ == "__main__":
    main()
