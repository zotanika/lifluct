"""Lightweight registry for experiment and run outputs."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from lifluct.core.failure_modes import failure_mode_names
from lifluct.types import CellSnapshot, RegimeConfig, RegistryRecord, RunConfig, RunSummary


def compute_config_hash(config: RunConfig | Mapping[str, Any]) -> str:
    payload = config.to_dict() if isinstance(config, RunConfig) else dict(config)
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def make_registry_record(
    *,
    experiment_id: str,
    run_id: str,
    run_dir: str | Path,
    label: str,
    config: RunConfig,
    summary: RunSummary,
    cell_snapshots: Sequence[CellSnapshot],
    warnings_count: int,
    failure_modes_count: int,
    failure_modes: Sequence[Any] | None = None,
    model_type: str | None = None,
    timestamp: str | None = None,
    diagnostics: Mapping[str, Any] | None = None,
    experiment_family: str = "",
    retention_mode: str = "full_trace",
) -> RegistryRecord:
    toxic_mode = config.toxic_mode or config.toxic_routing_mode
    detected_failure_modes = "; ".join(failure_mode_names(failure_modes or []))
    model_family = "no_lysis" if config.lysis_mode == "off" else "lysis_enabled"
    diagnostics = diagnostics or {}
    return RegistryRecord(
        experiment_id=experiment_id,
        run_id=run_id,
        config_hash=compute_config_hash(config),
        regime_id=RegimeConfig.from_run_config(config).regime_id(),
        seed=config.seed,
        timestamp=timestamp or utc_timestamp(),
        model_type=model_type or config.baseline_type,
        model_family=model_family,
        baseline_type=config.baseline_type,
        label=label,
        attribution_mode=config.attribution_mode,
        toxic_mode=toxic_mode,
        lysis_mode=config.lysis_mode,
        fitness_mode=config.fitness_mode,
        run_dir=str(run_dir),
        final_lp_minus_hodl_b=summary.lp_minus_hodl_b,
        lp_minus_hodl_b=summary.lp_minus_hodl_b,
        total_attributed_loss_b=summary.total_attributed_loss_b,
        total_lp_revenue_b=summary.total_lp_revenue_b,
        total_trader_cost_b=summary.total_trader_cost_b,
        total_arbitrage_profit_b=summary.total_arbitrage_profit_b,
        total_lysis_count=summary.total_lysis_count,
        total_dead_cells=summary.total_dead_cells,
        final_active_cells=final_active_cells(cell_snapshots),
        gene_dispersion_final=final_gene_dispersion(cell_snapshots),
        detected_failure_modes=detected_failure_modes,
        warnings_count=warnings_count,
        failure_modes_count=failure_modes_count,
        experiment_family=experiment_family,
        retention_mode=retention_mode,
        dominant_cell_concentration_final=_diagnostic_last_value(
            diagnostics.get("top_1_cell_volume_share_by_epoch", {})
        ),
    )


def write_registry(path: str | Path, records: Sequence[RegistryRecord]) -> Path:
    output = Path(path)
    rows = [record.to_dict() for record in records]
    with output.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return output
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return output


def append_registry_records(path: str | Path, records: Sequence[RegistryRecord]) -> Path:
    output = Path(path)
    rows = [record.to_dict() for record in records]
    if not rows:
        return output

    existing_rows = load_registry_rows(output)
    combined_rows = [*existing_rows, *rows]
    fieldnames = _merged_fieldnames(combined_rows)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in combined_rows])
    return output


def upsert_registry_records(path: str | Path, records: Sequence[RegistryRecord]) -> Path:
    output = Path(path)
    if not records:
        return output
    existing_rows = load_registry_rows(output)
    merged: dict[str, dict[str, Any]] = {str(row.get("run_id", "")): dict(row) for row in existing_rows}
    for record in records:
        merged[record.run_id] = record.to_dict()
    fieldnames = _merged_fieldnames(merged.values())
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in merged.values()])
    return output


def load_registry_rows(path: str | Path) -> list[dict[str, str]]:
    registry_path = Path(path)
    if not registry_path.exists():
        return []
    with registry_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _merged_fieldnames(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    ordered: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in ordered:
                ordered.append(key)
    return ordered


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def final_active_cells(cell_snapshots: Sequence[CellSnapshot]) -> int:
    if not cell_snapshots:
        return 0
    final_epoch = max(snapshot.epoch_index for snapshot in cell_snapshots)
    return sum(snapshot.active for snapshot in cell_snapshots if snapshot.epoch_index == final_epoch)


def final_gene_dispersion(cell_snapshots: Sequence[CellSnapshot]) -> float:
    if not cell_snapshots:
        return 0.0
    final_epoch = max(snapshot.epoch_index for snapshot in cell_snapshots)
    survivors = [snapshot for snapshot in cell_snapshots if snapshot.epoch_index == final_epoch]
    if len(survivors) <= 1:
        return 0.0

    def _std(values: list[float]) -> float:
        mean = sum(values) / len(values)
        return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5

    components = [
        _std([snapshot.f_min for snapshot in survivors]),
        _std([snapshot.mu for snapshot in survivors]),
        _std([snapshot.tau for snapshot in survivors]),
        _std([snapshot.beta for snapshot in survivors]),
    ]
    return sum(components) / len(components)


def _diagnostic_last_value(values: Mapping[str, Any] | Sequence[Any]) -> float:
    if isinstance(values, Mapping):
        if not values:
            return 0.0
        keys = sorted((int(key) for key in values.keys()))
        return float(values[str(keys[-1])] if str(keys[-1]) in values else values[keys[-1]])
    if isinstance(values, Sequence) and values:
        return float(values[-1])
    return 0.0
