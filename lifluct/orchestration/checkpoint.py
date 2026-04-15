"""Checkpoint and resume helpers for large-scale batches."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping, Sequence


def load_status_rows(path: str | Path) -> list[dict[str, str]]:
    status_path = Path(path)
    if not status_path.exists():
        return []
    with status_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def latest_status_by_run(path: str | Path) -> dict[str, dict[str, str]]:
    latest: dict[str, dict[str, str]] = {}
    for row in load_status_rows(path):
        latest[str(row.get("run_id", ""))] = row
    return latest


def upsert_status_row(path: str | Path, row: Mapping[str, Any]) -> Path:
    status_path = Path(path)
    rows = load_status_rows(status_path)
    latest: dict[str, dict[str, Any]] = {str(existing.get("run_id", "")): dict(existing) for existing in rows}
    latest[str(row.get("run_id", ""))] = dict(row)
    fieldnames = _merged_fieldnames(latest.values())
    with status_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{field: existing.get(field, "") for field in fieldnames} for existing in latest.values()])
    return status_path


def run_output_complete(run_dir: str | Path) -> bool:
    run_path = Path(run_dir)
    return (run_path / "summary.json").exists() and (run_path / "config_used.yaml").exists()


def _merged_fieldnames(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    ordered: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in ordered:
                ordered.append(key)
    return ordered
