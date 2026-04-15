"""Simple markdown and CSV table helpers for research reports."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Sequence


def write_rows_csv(path: str | Path, rows: Sequence[dict[str, Any]]) -> Path:
    output = Path(path)
    with output.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return output
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return output


def markdown_table(
    rows: Sequence[dict[str, Any]],
    *,
    columns: Sequence[str] | None = None,
    float_precision: int = 4,
) -> str:
    if not rows:
        return "_No rows._"

    selected_columns = list(columns) if columns is not None else list(rows[0].keys())
    header = "| " + " | ".join(_escape_markdown_cell(column) for column in selected_columns) + " |"
    divider = "| " + " | ".join("---" for _ in selected_columns) + " |"
    lines = [header, divider]
    for row in rows:
        values = [_format_value(row.get(column), float_precision=float_precision) for column in selected_columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def bullet_list(items: Sequence[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _format_value(value: Any, *, float_precision: int) -> str:
    if isinstance(value, float):
        rendered = f"{value:.{float_precision}f}"
    else:
        rendered = str(value)
    return _escape_markdown_cell(rendered)


def _escape_markdown_cell(value: str) -> str:
    sanitized = value.replace("\\", "\\\\")
    sanitized = sanitized.replace("|", "\\|")
    sanitized = sanitized.replace("\n", "<br>")
    return sanitized
