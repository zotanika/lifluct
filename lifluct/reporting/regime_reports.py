"""Markdown report writers for Phase 4.2 regime families and master adjudication."""

from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Sequence

from lifluct.reporting.tables import bullet_list


def write_regime_family_report_markdown(
    output_path: str | Path,
    *,
    title: str,
    family_definition_block: str,
    aggregate_table: str,
    comparator_block: str,
    verdict_block: str,
    plots_block: Sequence[str],
    notes: Sequence[str],
) -> Path:
    template = _load_template("regime_family_report_template.md")
    output = Path(output_path)
    rendered = template.safe_substitute(
        title=title,
        family_definition_block=family_definition_block,
        aggregate_table=aggregate_table,
        comparator_block=comparator_block,
        verdict_block=verdict_block,
        plots_block=bullet_list(list(plots_block)),
        notes_block=bullet_list(list(notes)),
    )
    output.write_text(rendered, encoding="utf-8")
    return output


def write_prevalence_report_markdown(
    output_path: str | Path,
    *,
    title: str,
    family_definition_block: str,
    prevalence_table: str,
    notes: Sequence[str],
) -> Path:
    template = _load_template("prevalence_report_template.md")
    output = Path(output_path)
    rendered = template.safe_substitute(
        title=title,
        family_definition_block=family_definition_block,
        prevalence_table=prevalence_table,
        notes_block=bullet_list(list(notes)),
    )
    output.write_text(rendered, encoding="utf-8")
    return output


def write_adjudication_master_markdown(
    output_path: str | Path,
    *,
    title: str,
    family_table: str,
    verdict_notes: Sequence[str],
    plots_block: Sequence[str],
) -> Path:
    template = _load_template("adjudication_master_template.md")
    output = Path(output_path)
    rendered = template.safe_substitute(
        title=title,
        family_table=family_table,
        verdict_notes_block=bullet_list(list(verdict_notes)),
        plots_block=bullet_list(list(plots_block)),
    )
    output.write_text(rendered, encoding="utf-8")
    return output


def _load_template(template_name: str) -> Template:
    template_path = Path(__file__).resolve().parents[2] / "reports" / "templates" / template_name
    return Template(template_path.read_text(encoding="utf-8"))
