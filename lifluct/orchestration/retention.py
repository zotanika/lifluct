"""Retention helpers for large-scale experiment runs."""

from __future__ import annotations

from typing import Any

from lifluct.types import RetentionMode

DEFAULT_HYBRID_DEBUG_FALLBACK: RetentionMode = "epoch_only"


def normalize_retention_mode(mode: str) -> RetentionMode:
    if mode not in {"full_trace", "epoch_only", "summary_only", "hybrid_debug"}:
        raise ValueError(f"unsupported retention mode: {mode}")
    return mode


def effective_retention_mode(
    requested_mode: str,
    *,
    run_index: int = 0,
    hybrid_debug_first_n: int = 0,
    hybrid_debug_fallback: str = DEFAULT_HYBRID_DEBUG_FALLBACK,
) -> RetentionMode:
    normalized = normalize_retention_mode(requested_mode)
    if normalized != "hybrid_debug":
        return normalized
    fallback = normalize_retention_mode(hybrid_debug_fallback)
    if fallback == "hybrid_debug":
        fallback = DEFAULT_HYBRID_DEBUG_FALLBACK
    return "full_trace" if run_index < max(0, hybrid_debug_first_n) else fallback


def retention_artifacts(mode: str) -> dict[str, Any]:
    normalized = normalize_retention_mode(mode)
    if normalized == "full_trace":
        return {
            "write_trades": True,
            "write_step_metrics": True,
            "write_epoch_summaries": True,
            "write_cell_snapshots": True,
            "write_plots": True,
        }
    if normalized == "epoch_only":
        return {
            "write_trades": False,
            "write_step_metrics": False,
            "write_epoch_summaries": True,
            "write_cell_snapshots": True,
            "write_plots": False,
        }
    if normalized == "summary_only":
        return {
            "write_trades": False,
            "write_step_metrics": False,
            "write_epoch_summaries": False,
            "write_cell_snapshots": False,
            "write_plots": False,
        }
    raise ValueError("hybrid_debug must be resolved before artifact selection")
