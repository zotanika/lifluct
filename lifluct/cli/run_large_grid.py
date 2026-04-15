"""Run a large Phase 4.2 regime-family batch."""

from __future__ import annotations

from lifluct.cli.run_regime_family import _run, main


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    parser = subparsers.add_parser("large-grid", help=__doc__)
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


if __name__ == "__main__":
    main()
