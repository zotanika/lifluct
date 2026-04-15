"""Parallel manifest execution for large-scale experiment batches."""

from __future__ import annotations

import math
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Sequence

from lifluct.cli.run_simulation import execute_and_write_run
from lifluct.orchestration.checkpoint import latest_status_by_run, run_output_complete, upsert_status_row
from lifluct.orchestration.manifest import RunManifestEntry
from lifluct.reporting.experiment_registry import load_registry_rows, make_registry_record, upsert_registry_records
from lifluct.reporting.loader import load_cell_snapshots, load_failure_modes, load_run_config, load_summary, load_validation_warnings
from lifluct.types import RegistryRecord, RunConfig


def run_manifest_entries(
    entries: Sequence[RunManifestEntry],
    *,
    family_dir: str | Path,
    max_workers: int = 1,
    resume: bool = True,
    shard_index: int = 0,
    shard_count: int = 1,
) -> dict[str, int]:
    family_path = Path(family_dir)
    family_path.mkdir(parents=True, exist_ok=True)
    registry_path = family_path / "registry.csv"
    status_path = family_path / "run_status.csv"

    existing_registry = {row["run_id"]: row for row in load_registry_rows(registry_path)}
    existing_status = latest_status_by_run(status_path)
    pending_entries: list[RunManifestEntry] = []
    completed = 0
    skipped = 0

    for entry in entries:
        run_dir = Path(entry.output_dir)
        if resume and entry.run_id in existing_registry:
            skipped += 1
            continue
        if resume and run_output_complete(run_dir):
            record = _recover_registry_record(entry, run_dir)
            upsert_registry_records(registry_path, [record])
            upsert_status_row(
                status_path,
                {
                    "run_id": entry.run_id,
                    "status": "completed",
                    "detail": "recovered_from_existing_output",
                    "shard_index": shard_index,
                    "shard_count": shard_count,
                },
            )
            completed += 1
            continue
        if resume and existing_status.get(entry.run_id, {}).get("status") == "completed":
            skipped += 1
            continue
        pending_entries.append(entry)

    start = time.perf_counter()
    failures = 0
    if max_workers <= 1:
        for index, entry in enumerate(pending_entries, start=1):
            outcome = _execute_entry_worker(entry, shard_index=shard_index, shard_count=shard_count)
            failures += _handle_worker_outcome(
                outcome,
                registry_path=registry_path,
                status_path=status_path,
            )
            _log_progress(index=index, total=len(pending_entries), start=start, completed=completed + index - failures, failures=failures, skipped=skipped)
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_execute_entry_worker, entry, shard_index=shard_index, shard_count=shard_count): entry.run_id
                for entry in pending_entries
            }
            processed = 0
            for future in as_completed(futures):
                processed += 1
                outcome = future.result()
                failures += _handle_worker_outcome(
                    outcome,
                    registry_path=registry_path,
                    status_path=status_path,
                )
                _log_progress(index=processed, total=len(pending_entries), start=start, completed=completed + processed - failures, failures=failures, skipped=skipped)

    return {
        "completed": completed + len(pending_entries) - failures,
        "failed": failures,
        "skipped": skipped,
        "total": len(entries),
    }


def _execute_entry_worker(
    entry: RunManifestEntry,
    *,
    shard_index: int,
    shard_count: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        config = RunConfig.from_mapping(entry.config)
        metadata = dict(entry.metadata)
        metadata.update(
            {
                "run_id": entry.run_id,
                "experiment_family": entry.experiment_family,
                "retention_mode": entry.retention_mode,
                "shard_index": shard_index,
                "shard_count": shard_count,
            }
        )
        result = execute_and_write_run(
            config=config,
            output_dir=entry.output_dir,
            metadata=metadata,
            retention_mode=entry.retention_mode,
        )
        record = make_registry_record(
            experiment_id=entry.experiment_family,
            run_id=entry.run_id,
            run_dir=entry.output_dir,
            label=entry.label,
            config=result.config,
            summary=result.summary,
            cell_snapshots=result.cell_snapshots,
            warnings_count=len(result.validation_warnings),
            failure_modes_count=len(result.failure_modes),
            failure_modes=result.failure_modes,
            model_type=entry.model_type,
            diagnostics=result.diagnostics,
            experiment_family=entry.experiment_family,
            retention_mode=entry.retention_mode,
        )
        return {
            "run_id": entry.run_id,
            "status": "completed",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "record": record.to_dict(),
            "shard_index": shard_index,
            "shard_count": shard_count,
        }
    except Exception as exc:  # pragma: no cover - exercised via integration tests
        return {
            "run_id": entry.run_id,
            "status": "failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "shard_index": shard_index,
            "shard_count": shard_count,
        }


def _handle_worker_outcome(
    outcome: dict[str, Any],
    *,
    registry_path: Path,
    status_path: Path,
) -> int:
    upsert_status_row(status_path, outcome)
    if outcome["status"] == "completed":
        upsert_registry_records(
            registry_path,
            [RegistryRecord(**outcome["record"])],
        )
        return 0
    return 1


def _recover_registry_record(entry: RunManifestEntry, run_dir: Path) -> RegistryRecord:
    config = load_run_config(run_dir / "config_used.yaml")
    summary = load_summary(run_dir / "summary.json")
    cell_snapshots = load_cell_snapshots(run_dir / "cell_snapshots.csv")
    warnings = load_validation_warnings(run_dir / "validation_warnings.json")
    failure_modes = load_failure_modes(run_dir / "failure_modes.json")
    diagnostics_path = run_dir / "diagnostics.json"
    diagnostics = {}
    if diagnostics_path.exists():
        diagnostics = __import__("json").loads(diagnostics_path.read_text(encoding="utf-8"))
    return make_registry_record(
        experiment_id=entry.experiment_family,
        run_id=entry.run_id,
        run_dir=run_dir,
        label=entry.label,
        config=config,
        summary=summary,
        cell_snapshots=cell_snapshots,
        warnings_count=len(warnings),
        failure_modes_count=len(failure_modes),
        failure_modes=failure_modes,
        model_type=entry.model_type,
        diagnostics=diagnostics,
        experiment_family=entry.experiment_family,
        retention_mode=entry.retention_mode,
    )


def _log_progress(
    *,
    index: int,
    total: int,
    start: float,
    completed: int,
    failures: int,
    skipped: int,
) -> None:
    elapsed = max(0.001, time.perf_counter() - start)
    throughput = index / elapsed
    remaining = max(0, total - index)
    eta_seconds = remaining / throughput if throughput > 0 else math.inf
    eta_text = "n/a" if not math.isfinite(eta_seconds) else f"{eta_seconds:0.1f}s"
    print(
        f"[phase42] processed={index}/{total} completed={completed} failed={failures} skipped={skipped} elapsed={elapsed:0.1f}s eta={eta_text}",
        flush=True,
    )
