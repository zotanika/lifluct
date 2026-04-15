"""Aggregate metric helpers for LIFLUCT run outputs."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from lifluct.types import CellSnapshot, EpochSummary, RunConfig, RunSummary, StepMetric, TradeRecord


def lp_minus_hodl(lp_value_b: float, hodl_value_b: float) -> float:
    return lp_value_b - hodl_value_b


def cumulative_fee_totals(step_metrics: Sequence[StepMetric]) -> dict[str, float]:
    last = step_metrics[-1]
    return {
        "lp_fee_b": last.cumulative_lp_fee_b,
        "protocol_fee_b": last.cumulative_protocol_fee_b,
        "total_fee_b": last.cumulative_lp_fee_b + last.cumulative_protocol_fee_b,
    }


def cumulative_attributed_loss(step_metrics: Sequence[StepMetric]) -> float:
    return step_metrics[-1].cumulative_attributed_loss_b


def cumulative_trader_cost(step_metrics: Sequence[StepMetric]) -> float:
    return step_metrics[-1].cumulative_trader_cost_b


def arbitrage_totals(step_metrics: Sequence[StepMetric]) -> float:
    return step_metrics[-1].cumulative_arbitrage_profit_b


def trade_counts_by_type(trades: Sequence[TradeRecord]) -> dict[str, int]:
    counts = Counter(trade.actor_type for trade in trades)
    return {
        "total": len(trades),
        "noise": counts.get("noise", 0),
        "arbitrage": counts.get("arbitrage", 0),
    }


def build_summary_from_outputs(
    config: RunConfig,
    trades: Sequence[TradeRecord],
    step_metrics: Sequence[StepMetric],
    epoch_summaries: Sequence[EpochSummary] | None = None,
    cell_snapshots: Sequence[CellSnapshot] | None = None,
) -> RunSummary:
    final_step = step_metrics[-1]
    trade_counts = trade_counts_by_type(trades)
    epoch_summaries = epoch_summaries or []
    return RunSummary(
        final_lp_value_b=final_step.lp_value_b,
        final_hodl_value_b=final_step.hodl_value_b,
        lp_minus_hodl_b=lp_minus_hodl(final_step.lp_value_b, final_step.hodl_value_b),
        total_lp_revenue_b=final_step.cumulative_lp_fee_b,
        total_protocol_revenue_b=final_step.cumulative_protocol_fee_b,
        total_lp_fee_b=final_step.cumulative_lp_fee_b,
        total_protocol_fee_b=final_step.cumulative_protocol_fee_b,
        total_attributed_loss_b=final_step.cumulative_attributed_loss_b,
        total_trader_cost_b=final_step.cumulative_trader_cost_b,
        total_arbitrage_profit_b=final_step.cumulative_arbitrage_profit_b,
        num_trades=trade_counts["total"],
        num_noise_trades=trade_counts["noise"],
        num_arbitrage_trades=trade_counts["arbitrage"],
        total_lysis_count=sum(epoch.num_lysed_cells for epoch in epoch_summaries),
        total_dead_cells=sum(epoch.num_dead_cells for epoch in epoch_summaries),
    )
