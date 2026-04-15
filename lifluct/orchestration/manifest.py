"""Manifest builders for large-scale regime-family experiments."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from lifluct.core.benchmark import build_model_config_for_type, regime_for_family
from lifluct.core.cell import CellGenes
from lifluct.orchestration.retention import DEFAULT_HYBRID_DEBUG_FALLBACK, effective_retention_mode
from lifluct.reporting.experiment_registry import compute_config_hash
from lifluct.reporting.loader import load_run_config
from lifluct.types import ComparisonFamily, RegimeConfig, RetentionMode, RunConfig


@dataclass(slots=True, frozen=True)
class RegimeSpec:
    regime_id: str
    config: RunConfig


@dataclass(slots=True, frozen=True)
class ExperimentFamilyConfig:
    family_name: str
    description: str
    comparison_family: ComparisonFamily
    models: tuple[str, ...]
    seed_start: int
    seed_count: int
    retention_mode: RetentionMode
    hybrid_debug_first_n: int = 0
    hybrid_debug_fallback: RetentionMode = DEFAULT_HYBRID_DEBUG_FALLBACK
    lysis_allowed: bool = False
    attribution_robustness_required: bool = False
    best_fixed_candidate_config: str | None = None
    best_fixed_search_manifest: str | None = None
    best_fixed_genes: CellGenes | None = None
    regimes: tuple[RegimeSpec, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class RunManifestEntry:
    run_id: str
    experiment_family: str
    regime_id: str
    model_type: str
    config_hash: str
    seed: int
    retention_mode: RetentionMode
    shard_index: int
    shard_count: int
    output_dir: str
    label: str
    comparison_family: str
    config: dict[str, Any]
    metadata: dict[str, Any]

    def to_row(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_family": self.experiment_family,
            "regime_id": self.regime_id,
            "model_type": self.model_type,
            "config_hash": self.config_hash,
            "seed": self.seed,
            "retention_mode": self.retention_mode,
            "shard_index": self.shard_index,
            "shard_count": self.shard_count,
            "output_dir": self.output_dir,
            "label": self.label,
            "comparison_family": self.comparison_family,
            "config_json": json.dumps(self.config, sort_keys=True),
            "metadata_json": json.dumps(self.metadata, sort_keys=True),
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "RunManifestEntry":
        return cls(
            run_id=str(row["run_id"]),
            experiment_family=str(row["experiment_family"]),
            regime_id=str(row["regime_id"]),
            model_type=str(row["model_type"]),
            config_hash=str(row["config_hash"]),
            seed=int(row["seed"]),
            retention_mode=str(row["retention_mode"]),  # type: ignore[arg-type]
            shard_index=int(row.get("shard_index", -1)),
            shard_count=int(row.get("shard_count", 1)),
            output_dir=str(row["output_dir"]),
            label=str(row.get("label", row["run_id"])),
            comparison_family=str(row.get("comparison_family", "")),
            config=json.loads(str(row["config_json"])),
            metadata=json.loads(str(row["metadata_json"])),
        )


def load_family_manifest(path: str | Path) -> ExperimentFamilyConfig:
    manifest_path = Path(path)
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    base_dir = manifest_path.parent
    regimes = tuple(_load_regime_specs(raw.get("regimes", []), base_dir))
    if not regimes:
        raise ValueError("family manifest must define at least one regime")
    best_fixed_genes = None
    if isinstance(raw.get("best_fixed_genes"), Mapping):
        best_fixed_genes = CellGenes(**raw["best_fixed_genes"])
    return ExperimentFamilyConfig(
        family_name=str(raw.get("family_name", manifest_path.stem)),
        description=str(raw.get("description", "")),
        comparison_family=str(raw.get("comparison_family", "no_lysis")),  # type: ignore[arg-type]
        models=tuple(raw.get("models", [])),
        seed_start=int(raw.get("seed_start", 1)),
        seed_count=int(raw.get("seed_count", len(raw.get("seeds", [])) or 1)),
        retention_mode=str(raw.get("retention_mode", "summary_only")),  # type: ignore[arg-type]
        hybrid_debug_first_n=int(raw.get("hybrid_debug_first_n", 0)),
        hybrid_debug_fallback=str(raw.get("hybrid_debug_fallback", DEFAULT_HYBRID_DEBUG_FALLBACK)),  # type: ignore[arg-type]
        lysis_allowed=bool(raw.get("lysis_allowed", False)),
        attribution_robustness_required=bool(raw.get("attribution_robustness_required", False)),
        best_fixed_candidate_config=_resolve_optional_path(raw.get("best_fixed_candidate_config"), base_dir),
        best_fixed_search_manifest=_resolve_optional_path(raw.get("best_fixed_search_manifest"), base_dir),
        best_fixed_genes=best_fixed_genes,
        regimes=regimes,
    )


def build_run_manifest(
    family: ExperimentFamilyConfig,
    *,
    output_root: str | Path,
    models_subset: Sequence[str] | None = None,
    seed_override: int | None = None,
    retention_override: str | None = None,
    best_fixed_genes: CellGenes | None = None,
) -> list[RunManifestEntry]:
    selected_models = tuple(models_subset) if models_subset else family.models
    if not selected_models:
        raise ValueError("family must define at least one model")
    seeds = [seed_override] if seed_override is not None else list(range(family.seed_start, family.seed_start + family.seed_count))
    resolved_best_fixed = best_fixed_genes or family.best_fixed_genes or _load_best_fixed_genes(family.best_fixed_candidate_config)
    if any(model.startswith("best_fixed_single_cell") for model in selected_models) and resolved_best_fixed is None:
        raise ValueError(
            "best-fixed model requested but no best_fixed_genes or best_fixed_candidate_config was provided"
        )
    normalized_retention = retention_override or family.retention_mode
    output_dir = Path(output_root)

    entries: list[RunManifestEntry] = []
    run_index = 0
    for regime_spec in family.regimes:
        regime = regime_for_family(RegimeConfig.from_run_config(regime_spec.config), family.comparison_family)
        for model_type in selected_models:
            for seed in seeds:
                concrete = build_model_config_for_type(
                    model_type=model_type,
                    template_config=replace(regime_spec.config, seed=seed),
                    regime=replace(regime, seed=seed),
                    best_fixed_genes=resolved_best_fixed,
                )
                effective_mode = effective_retention_mode(
                    normalized_retention,
                    run_index=run_index,
                    hybrid_debug_first_n=family.hybrid_debug_first_n,
                    hybrid_debug_fallback=family.hybrid_debug_fallback,
                )
                run_id = f"{family.family_name}__{regime.regime_id()}__{model_type}__seed{seed:04d}"
                metadata = {
                    "experiment_family": family.family_name,
                    "regime_id": regime.regime_id(),
                    "model_type": model_type,
                    "model_family": family.comparison_family,
                    "label": f"{model_type}@{regime_spec.regime_id}",
                    "retention_mode": effective_mode,
                }
                entries.append(
                    RunManifestEntry(
                        run_id=run_id,
                        experiment_family=family.family_name,
                        regime_id=regime.regime_id(),
                        model_type=model_type,
                        config_hash=compute_config_hash(concrete),
                        seed=seed,
                        retention_mode=effective_mode,
                        shard_index=-1,
                        shard_count=1,
                        output_dir=str(output_dir / run_id),
                        label=str(metadata["label"]),
                        comparison_family=family.comparison_family,
                        config=concrete.to_dict(),
                        metadata=metadata,
                    )
                )
                run_index += 1
    return entries


def write_manifest(path: str | Path, entries: Sequence[RunManifestEntry]) -> Path:
    manifest_path = Path(path)
    rows = [entry.to_row() for entry in entries]
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return manifest_path
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return manifest_path


def load_manifest_entries(path: str | Path) -> list[RunManifestEntry]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return []
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        return [RunManifestEntry.from_row(row) for row in csv.DictReader(handle)]


def _load_regime_specs(entries: Sequence[Any], base_dir: Path) -> list[RegimeSpec]:
    regimes: list[RegimeSpec] = []
    for index, entry in enumerate(entries):
        if isinstance(entry, str):
            config_path = _resolve_path(entry, base_dir)
            config = load_run_config(config_path)
            regimes.append(RegimeSpec(regime_id=Path(config_path).stem, config=config))
            continue
        if not isinstance(entry, Mapping):
            raise ValueError(f"unsupported regime entry: {entry}")
        if "path" in entry or "base_config" in entry:
            config_path = _resolve_path(str(entry.get("path") or entry.get("base_config")), base_dir)
            config = load_run_config(config_path)
        else:
            config = RunConfig.from_mapping(dict(entry.get("config", entry)))
        overrides = dict(entry.get("overrides", {}))
        if overrides:
            config = replace(config, **overrides)
        regime_id = str(entry.get("regime_id", f"regime_{index:02d}"))
        regimes.append(RegimeSpec(regime_id=regime_id, config=config))
    return regimes


def _load_best_fixed_genes(best_fixed_candidate_config: str | None) -> CellGenes | None:
    if best_fixed_candidate_config is None:
        return None
    config = load_run_config(best_fixed_candidate_config)
    return CellGenes(
        f_min=config.f_min,
        mu=config.mu,
        tau=config.tau,
        beta=config.beta,
    )


def _resolve_path(raw_path: str, base_dir: Path) -> str:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return str(candidate)


def _resolve_optional_path(raw_path: Any, base_dir: Path) -> str | None:
    if raw_path in {None, ""}:
        return None
    return _resolve_path(str(raw_path), base_dir)
