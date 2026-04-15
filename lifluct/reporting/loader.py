"""Load configs and run outputs from disk."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from lifluct.types import (
    CellSnapshot,
    EpochSummary,
    FailureModeObservation,
    RunConfig,
    RunSummary,
    StepMetric,
    TradeRecord,
    ValidationWarning,
)


def load_run_config(path: str | Path) -> RunConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return RunConfig.from_mapping(raw)


def load_trade_records(path: str | Path) -> list[TradeRecord]:
    rows = _load_csv(path)
    return [
        TradeRecord(
            trade_id=int(row["trade_id"]),
            step=int(row["step"]),
            actor_type=row["actor_type"],
            direction=row["direction"],
            amount_in=float(row["amount_in"]),
            amount_out=float(row["amount_out"]),
            notional_b=float(row["notional_b"]),
            exec_price=float(row["exec_price"]),
            oracle_price=float(row["oracle_price"]),
            pool_price_before=float(row["pool_price_before"]),
            pool_price_after=float(row["pool_price_after"]),
            fee_rate=float(row["fee_rate"]),
            lp_fee_amount_b=float(row["lp_fee_amount_b"]),
            protocol_fee_amount_b=float(row["protocol_fee_amount_b"]),
            attributed_loss_b=float(row["attributed_loss_b"]),
            trader_cost_b=float(row["trader_cost_b"]),
            epoch_index=int(row.get("epoch_index", 0)),
            routing_mode=row.get("routing_mode", ""),
            cell_id=int(row["cell_id"]) if row.get("cell_id") not in {None, ""} else None,
        )
        for row in rows
    ]


def load_step_metrics(path: str | Path) -> list[StepMetric]:
    rows = _load_csv(path)
    return [
        StepMetric(
            step=int(row["step"]),
            true_price=float(row["true_price"]),
            observed_price=float(row["observed_price"]),
            pool_price=float(row["pool_price"]),
            reserve_a=float(row["reserve_a"]),
            reserve_b=float(row["reserve_b"]),
            tvl_b=float(row["tvl_b"]),
            lp_value_b=float(row["lp_value_b"]),
            hodl_value_b=float(row["hodl_value_b"]),
            cumulative_lp_fee_b=float(row["cumulative_lp_fee_b"]),
            cumulative_protocol_fee_b=float(row["cumulative_protocol_fee_b"]),
            cumulative_attributed_loss_b=float(row["cumulative_attributed_loss_b"]),
            cumulative_trader_cost_b=float(row["cumulative_trader_cost_b"]),
            cumulative_arbitrage_profit_b=float(row["cumulative_arbitrage_profit_b"]),
            num_trades=int(row["num_trades"]),
            epoch_index=int(row.get("epoch_index", 0)),
            num_active_cells=int(row.get("num_active_cells", 1)),
            num_lysed_cells=int(row.get("num_lysed_cells", 0)),
        )
        for row in rows
    ]


def load_epoch_summaries(path: str | Path) -> list[EpochSummary]:
    rows = _load_csv(path)
    return [
        EpochSummary(
            epoch_index=int(row["epoch_index"]),
            num_active_cells=int(row["num_active_cells"]),
            num_lysed_cells=int(row["num_lysed_cells"]),
            num_dead_cells=int(row["num_dead_cells"]),
            mean_fitness=float(row["mean_fitness"]),
            median_fitness=float(row["median_fitness"]),
            total_lp_revenue_b=float(row["total_lp_revenue_b"]),
            total_protocol_revenue_b=float(row["total_protocol_revenue_b"]),
            total_attributed_loss_b=float(row["total_attributed_loss_b"]),
            total_trader_cost_b=float(row["total_trader_cost_b"]),
            total_volume_b=float(row["total_volume_b"]),
            avg_fee_rate=float(row["avg_fee_rate"]),
            top_cell_ids=json.loads(row["top_cell_ids"]),
            top_cell_gene_summary=row["top_cell_gene_summary"],
        )
        for row in rows
    ]


def load_cell_snapshots(path: str | Path) -> list[CellSnapshot]:
    rows = _load_csv(path)
    return [
        CellSnapshot(
            epoch_index=int(row["epoch_index"]),
            cell_id=int(row["cell_id"]),
            active=row["active"].lower() == "true",
            lysis_triggered=row["lysis_triggered"].lower() == "true",
            generation_index=int(row["generation_index"]),
            parent_cell_id=int(row["parent_cell_id"]) if row["parent_cell_id"] not in {"", "None"} else None,
            f_min=float(row["f_min"]),
            mu=float(row["mu"]),
            tau=float(row["tau"]),
            beta=float(row["beta"]),
            epoch_volume_b=float(row["epoch_volume_b"]),
            epoch_lp_revenue_b=float(row["epoch_lp_revenue_b"]),
            epoch_protocol_revenue_b=float(row["epoch_protocol_revenue_b"]),
            epoch_trader_cost_b=float(row["epoch_trader_cost_b"]),
            epoch_attributed_loss_b=float(row["epoch_attributed_loss_b"]),
            epoch_fees_total_b=float(row["epoch_fees_total_b"]),
            fitness=float(row["fitness"]),
        )
        for row in rows
    ]


def load_summary(path: str | Path) -> RunSummary:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return RunSummary(**raw)


def load_validation_warnings(path: str | Path) -> list[ValidationWarning]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return [ValidationWarning(**row) for row in raw]


def load_failure_modes(path: str | Path) -> list[FailureModeObservation]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return [FailureModeObservation(**row) for row in raw]


def load_run_directory(run_dir: str | Path) -> dict[str, Any]:
    run_path = Path(run_dir)
    data: dict[str, Any] = {
        "run_dir": run_path,
        "config": load_run_config(run_path / "config_used.yaml"),
        "trades": load_trade_records(run_path / "trades.csv"),
        "step_metrics": load_step_metrics(run_path / "step_metrics.csv"),
    }
    summary_path = run_path / "summary.json"
    epoch_summaries_path = run_path / "epoch_summaries.csv"
    cell_snapshots_path = run_path / "cell_snapshots.csv"
    validation_warnings_path = run_path / "validation_warnings.json"
    failure_modes_path = run_path / "failure_modes.json"
    diagnostics_path = run_path / "diagnostics.json"
    attribution_ranking_path = run_path / "attribution_ranking_stability.json"
    metadata_path = run_path / "run_metadata.json"
    if summary_path.exists():
        data["summary"] = load_summary(summary_path)
    if epoch_summaries_path.exists():
        data["epoch_summaries"] = load_epoch_summaries(epoch_summaries_path)
    if cell_snapshots_path.exists():
        data["cell_snapshots"] = load_cell_snapshots(cell_snapshots_path)
    if validation_warnings_path.exists():
        data["validation_warnings"] = load_validation_warnings(validation_warnings_path)
    if failure_modes_path.exists():
        data["failure_modes"] = load_failure_modes(failure_modes_path)
    if diagnostics_path.exists():
        data["diagnostics"] = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    if attribution_ranking_path.exists():
        data["attribution_ranking_stability"] = json.loads(attribution_ranking_path.read_text(encoding="utf-8"))
    if metadata_path.exists():
        data["metadata"] = json.loads(metadata_path.read_text(encoding="utf-8"))
    return data


def _load_csv(path: str | Path) -> list[dict[str, str]]:
    if not Path(path).exists():
        return []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
