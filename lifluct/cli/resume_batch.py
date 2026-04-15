"""Resume a previously started Phase 4.2 family batch."""

from __future__ import annotations

import argparse
from pathlib import Path

from lifluct.cli.aggregate_results import aggregate_family_directory
from lifluct.orchestration.manifest import load_manifest_entries
from lifluct.orchestration.scheduler import run_manifest_entries
from lifluct.orchestration.shard import shard_entries


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("resume", help=__doc__)
    parser.add_argument("--family-dir", required=True, help="Path to an existing family output directory")
    parser.add_argument("--manifest", help="Optional manifest CSV path")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--shard-index", type=int, default=0, help="Zero-based shard index")
    parser.add_argument("--shard-count", type=int, default=1, help="Total shard count")
    parser.add_argument("--aggregate", action="store_true", help="Regenerate aggregate outputs after resuming")
    parser.set_defaults(func=_run)


def _run(args) -> None:
    family_dir = Path(args.family_dir)
    manifest_path = Path(args.manifest) if args.manifest else family_dir / "manifest.csv"
    entries = load_manifest_entries(manifest_path)
    sharded = shard_entries(entries, shard_index=args.shard_index, shard_count=args.shard_count)
    run_manifest_entries(
        sharded,
        family_dir=family_dir,
        max_workers=args.workers,
        resume=True,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
    )
    if args.aggregate and args.shard_count == 1:
        aggregate_family_directory(family_dir)
    print(family_dir)


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-dir", required=True, help="Path to an existing family output directory")
    parser.add_argument("--manifest", help="Optional manifest CSV path")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--shard-index", type=int, default=0, help="Zero-based shard index")
    parser.add_argument("--shard-count", type=int, default=1, help="Total shard count")
    parser.add_argument("--aggregate", action="store_true", help="Regenerate aggregate outputs after resuming")
    args = parser.parse_args()
    _run(args)


if __name__ == "__main__":
    main()
