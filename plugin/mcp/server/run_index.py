"""Lightweight SQLite index for tracking LIFLUCT runs across sessions."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunIndex:
    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".lifluct" / "runs.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                run_dir TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                config_hash TEXT NOT NULL DEFAULT '',
                config_summary TEXT NOT NULL DEFAULT '{}',
                summary_metrics TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def register(self, *, run_id: str, run_dir: str, label: str = "",
                 config_hash: str = "", config_summary: dict[str, Any] | None = None,
                 summary_metrics: dict[str, Any] | None = None) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, run_dir, label, config_hash, config_summary, summary_metrics, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, run_dir, label, config_hash,
             json.dumps(config_summary or {}), json.dumps(summary_metrics or {}),
             datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def list_runs(self, *, filter_label: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if filter_label:
            rows = self._conn.execute(
                "SELECT * FROM runs WHERE label LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{filter_label}%", limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["config_summary"] = json.loads(d["config_summary"])
        d["summary_metrics"] = json.loads(d["summary_metrics"])
        return d
