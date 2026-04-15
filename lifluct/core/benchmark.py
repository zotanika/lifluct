"""Benchmark helpers for fair regime-by-model evaluation."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, replace
from typing import Sequence

import numpy as np

from lifluct.core.cell import CellGenes
from lifluct.core.simulation import SimulationRunner
from lifluct.types import ComparisonFamily, RegimeConfig, RunConfig, SimulationResult

SERIOUS_SEARCH_BUDGET = 128
SMOKE_SEARCH_BUDGET = 8
SEARCH_METHOD = "random_search"


@dataclass(slots=True)
class FixedSearchCandidate:
    candidate_id: int
    genes: CellGenes
    train_score: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "candidate_id": self.candidate_id,
            "f_min": self.genes.f_min,
            "mu": self.genes.mu,
            "tau": self.genes.tau,
            "beta": self.genes.beta,
            "train_score": self.train_score,
        }


@dataclass(slots=True)
class FixedSearchResult:
    best_genes: CellGenes
    best_train_score: float
    candidates: list[FixedSearchCandidate]
    train_rows: list[dict[str, float | int | str]]
    test_rows: list[dict[str, float | int | str]]
    search_budget: int
    search_method: str
    search_profile: str
    aggregate_mode: str = "mean"


def search_best_fixed_single_cell(
    *,
    train_configs: Sequence[RunConfig],
    search_budget: int,
    objective_mode: str,
    search_seed: int,
    test_configs: Sequence[RunConfig] | None = None,
    search_profile: str = "serious",
    family: ComparisonFamily | None = None,
    aggregate_mode: str = "mean",
) -> FixedSearchResult:
    if not train_configs:
        raise ValueError("train_configs must not be empty")

    rng = np.random.default_rng(search_seed)
    candidates: list[FixedSearchCandidate] = []
    train_rows: list[dict[str, float | int | str]] = []

    seed_config = train_configs[0]
    default_genes = CellGenes(
        f_min=seed_config.f_min,
        mu=seed_config.mu,
        tau=seed_config.tau,
        beta=seed_config.beta,
    )
    all_candidates = [default_genes]
    while len(all_candidates) < max(1, search_budget):
        all_candidates.append(sample_candidate_genes(seed_config, rng))

    best_genes = default_genes
    best_score = float("-inf")
    for candidate_id, genes in enumerate(all_candidates):
        rows, score = evaluate_fixed_genes_on_configs(
            genes=genes,
            configs=train_configs,
            objective_mode=objective_mode,
            dataset_name="train",
            family=family,
            aggregate_mode=aggregate_mode,
        )
        candidates.append(FixedSearchCandidate(candidate_id=candidate_id, genes=genes, train_score=score))
        train_rows.extend(rows)
        if score > best_score:
            best_score = score
            best_genes = genes

    test_rows: list[dict[str, float | int | str]] = []
    if test_configs:
        rows, _ = evaluate_fixed_genes_on_configs(
            genes=best_genes,
            configs=test_configs,
            objective_mode=objective_mode,
            dataset_name="test",
            family=family,
            aggregate_mode=aggregate_mode,
        )
        test_rows.extend(rows)

    return FixedSearchResult(
        best_genes=best_genes,
        best_train_score=best_score,
        candidates=candidates,
        train_rows=train_rows,
        test_rows=test_rows,
        search_budget=search_budget,
        search_method=SEARCH_METHOD,
        search_profile=search_profile,
        aggregate_mode=aggregate_mode,
    )


def evaluate_fixed_genes_on_configs(
    *,
    genes: CellGenes,
    configs: Sequence[RunConfig],
    objective_mode: str,
    dataset_name: str,
    family: ComparisonFamily | None = None,
    aggregate_mode: str = "mean",
) -> tuple[list[dict[str, float | int | str]], float]:
    rows: list[dict[str, float | int | str]] = []
    scores: list[float] = []
    for config in configs:
        regime = RegimeConfig.from_run_config(config)
        if family is not None:
            regime = regime_for_family(regime, family)
        run_config = build_fixed_single_cell_config(config, genes, regime=regime)
        result = SimulationRunner(run_config).run_single()
        objective_value = objective_score(result, objective_mode)
        scores.append(objective_value)
        rows.append(
            {
                "dataset": dataset_name,
                "evaluation_split": dataset_name,
                "seed": run_config.seed,
                "regime_id": regime.regime_id(),
                "sigma": regime.sigma,
                "oracle_mode": regime.oracle_mode,
                "oracle_lag_steps": regime.oracle_lag_steps,
                "toxic_mode": regime.toxic_mode,
                "lysis_mode": regime.lysis_mode,
                "search_method": SEARCH_METHOD,
                "objective": objective_value,
                "lp_minus_hodl_b": result.summary.lp_minus_hodl_b,
                "total_lp_revenue_b": result.summary.total_lp_revenue_b,
                "total_attributed_loss_b": result.summary.total_attributed_loss_b,
                "total_trader_cost_b": result.summary.total_trader_cost_b,
                "f_min": genes.f_min,
                "mu": genes.mu,
                "tau": genes.tau,
                "beta": genes.beta,
            }
        )
    return rows, aggregate_objective_values(scores, aggregate_mode=aggregate_mode)


def evaluate_model_suite(
    *,
    template_configs: Sequence[RunConfig],
    best_fixed_genes: CellGenes,
    family: ComparisonFamily,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for config in template_configs:
        regime = regime_for_family(RegimeConfig.from_run_config(config), family)
        suite = build_model_suite_for_regime(
            template_config=config,
            regime=regime,
            family=family,
            best_fixed_genes=best_fixed_genes,
        )
        assert_suite_regime_fairness(suite, regime, family=family)
        for model_type, model_config in suite.items():
            result = SimulationRunner(model_config).run_single()
            rows.append(
                {
                    "model_type": model_type,
                    "model_family": family,
                    "seed": model_config.seed,
                    "regime_id": regime.regime_id(),
                    "sigma": regime.sigma,
                    "oracle_mode": regime.oracle_mode,
                    "oracle_lag_steps": regime.oracle_lag_steps,
                    "toxic_mode": regime.toxic_mode,
                    "lysis_mode": regime.lysis_mode,
                    "lp_minus_hodl_b": result.summary.lp_minus_hodl_b,
                    "total_lp_revenue_b": result.summary.total_lp_revenue_b,
                    "total_attributed_loss_b": result.summary.total_attributed_loss_b,
                    "total_trader_cost_b": result.summary.total_trader_cost_b,
                    "total_lysis_count": result.summary.total_lysis_count,
                }
            )
    return rows


def build_model_suite_for_regime(
    *,
    template_config: RunConfig,
    regime: RegimeConfig,
    family: ComparisonFamily,
    best_fixed_genes: CellGenes,
) -> dict[str, RunConfig]:
    normalized_family = normalize_family(family)
    family_regime = regime_for_family(regime, normalized_family)
    base = apply_regime_to_config(template_config, family_regime)

    if normalized_family == "no_lysis":
        return {
            "static_cpmm": build_static_config(base, regime=family_regime),
            "dynamic_fee_single": build_dynamic_config(base, regime=family_regime),
            "best_fixed_single_cell": build_fixed_single_cell_config(base, best_fixed_genes, regime=family_regime),
            "lifluct_multi_cell_no_lysis": build_lifluct_config(base, regime=family_regime),
        }

    return {
        "dynamic_fee_single_with_lysis": build_dynamic_config(base, regime=family_regime),
        "best_fixed_single_cell_with_lysis": build_fixed_single_cell_config(base, best_fixed_genes, regime=family_regime),
        "lifluct_multi_cell_with_lysis": build_lifluct_config(base, regime=family_regime),
    }


def build_model_config_for_type(
    *,
    model_type: str,
    template_config: RunConfig,
    regime: RegimeConfig,
    best_fixed_genes: CellGenes | None = None,
) -> RunConfig:
    normalized = model_type.strip()
    base = apply_regime_to_config(template_config, regime)
    if normalized == "static_cpmm":
        return build_static_config(base, regime=replace(regime, lysis_mode="off"))
    if normalized in {"dynamic_fee_single", "dynamic_fee_single_with_lysis"}:
        applied_regime = replace(regime, lysis_mode="off") if normalized == "dynamic_fee_single" else regime
        return build_dynamic_config(base, regime=applied_regime)
    if normalized in {"lifluct_multi_cell", "lifluct_multi_cell_no_lysis", "lifluct_multi_cell_with_lysis"}:
        applied_regime = replace(regime, lysis_mode="off") if normalized in {"lifluct_multi_cell", "lifluct_multi_cell_no_lysis"} else regime
        return build_lifluct_config(base, regime=applied_regime)
    if normalized in {"best_fixed_single_cell", "best_fixed_single_cell_with_lysis"}:
        if best_fixed_genes is None:
            raise ValueError(f"model `{normalized}` requires best_fixed_genes")
        applied_regime = replace(regime, lysis_mode="off") if normalized == "best_fixed_single_cell" else regime
        return build_fixed_single_cell_config(base, best_fixed_genes, regime=applied_regime)
    raise ValueError(f"unsupported model_type: {model_type}")


def build_static_config(config: RunConfig, *, regime: RegimeConfig) -> RunConfig:
    return replace(
        apply_regime_to_config(config, regime),
        baseline_type="static_cpmm",
        num_cells=1,
        enable_evolution=False,
        use_dynamic_fee=False,
        use_turgor=False,
        lysis_mode="off",
        toxic_mode=regime.toxic_mode,
    )


def build_dynamic_config(config: RunConfig, *, regime: RegimeConfig) -> RunConfig:
    return replace(
        apply_regime_to_config(config, regime),
        baseline_type="dynamic_fee_single",
        num_cells=1,
        enable_evolution=False,
        use_dynamic_fee=True,
        use_turgor=False,
        beta=0.0,
    )


def build_lifluct_config(config: RunConfig, *, regime: RegimeConfig) -> RunConfig:
    return replace(
        apply_regime_to_config(config, regime),
        baseline_type="lifluct_multi_cell",
        use_dynamic_fee=True,
        use_turgor=True,
    )


def build_fixed_single_cell_config(
    config: RunConfig,
    genes: CellGenes,
    *,
    regime: RegimeConfig | None = None,
) -> RunConfig:
    applied = apply_regime_to_config(config, regime) if regime is not None else config
    return replace(
        applied,
        baseline_type="best_fixed_single_cell",
        num_cells=1,
        enable_evolution=False,
        elite_count=0,
        use_dynamic_fee=True,
        use_turgor=True,
        f_min=genes.f_min,
        mu=genes.mu,
        tau=genes.tau,
        beta=genes.beta,
    )


def apply_regime_to_config(config: RunConfig, regime: RegimeConfig | None) -> RunConfig:
    if regime is None:
        return config
    return replace(config, **regime.to_run_overrides())


def sample_candidate_genes(config: RunConfig, rng: np.random.Generator) -> CellGenes:
    return CellGenes(
        f_min=float(rng.uniform(config.f_min_min, config.f_min_max)),
        mu=float(rng.uniform(config.mu_min, config.mu_max)),
        tau=float(rng.uniform(config.tau_min, config.tau_max)),
        beta=float(rng.uniform(config.beta_min, config.beta_max)),
    )


def objective_score(result: SimulationResult, objective_mode: str) -> float:
    summary = result.summary
    if objective_mode == "lp_minus_hodl":
        return summary.lp_minus_hodl_b
    if objective_mode == "lp_minus_hodl_minus_trader_cost":
        return summary.lp_minus_hodl_b - summary.total_trader_cost_b
    if objective_mode == "balanced":
        return summary.total_lp_revenue_b - summary.total_attributed_loss_b - summary.total_trader_cost_b
    raise ValueError(f"unsupported objective mode: {objective_mode}")


def aggregate_objective_values(values: Sequence[float], *, aggregate_mode: str) -> float:
    if not values:
        return float("-inf")
    if aggregate_mode == "mean":
        return statistics.fmean(values)
    if aggregate_mode == "median":
        return statistics.median(values)
    if aggregate_mode == "penalized_mean":
        downside = [min(0.0, value) for value in values]
        return statistics.fmean(values) + 0.5 * statistics.fmean(downside)
    if aggregate_mode == "downside_robust":
        median = statistics.median(values)
        downside_penalty = statistics.fmean(abs(min(0.0, value)) for value in values)
        return median - downside_penalty
    raise ValueError(f"unsupported aggregate_mode: {aggregate_mode}")


def normalize_family(family: str) -> ComparisonFamily:
    if family not in {"no_lysis", "lysis_enabled"}:
        raise ValueError(f"unsupported comparison family: {family}")
    return family


def family_model_types(family: ComparisonFamily) -> list[str]:
    if family == "no_lysis":
        return [
            "static_cpmm",
            "dynamic_fee_single",
            "best_fixed_single_cell",
            "lifluct_multi_cell_no_lysis",
        ]
    return [
        "dynamic_fee_single_with_lysis",
        "best_fixed_single_cell_with_lysis",
        "lifluct_multi_cell_with_lysis",
    ]


def assert_suite_regime_fairness(
    suite: dict[str, RunConfig],
    regime: RegimeConfig,
    *,
    family: ComparisonFamily,
) -> None:
    normalized_family = normalize_family(family)
    expected_regime = regime_for_family(regime, normalized_family)
    for model_type, config in suite.items():
        actual = RegimeConfig.from_run_config(config)
        if actual != expected_regime:
            raise ValueError(
                f"Model `{model_type}` diverged from suite regime `{expected_regime.regime_id()}`."
            )
        if normalized_family == "no_lysis" and config.lysis_mode != "off":
            raise ValueError(f"Model `{model_type}` unexpectedly enabled lysis in no-lysis family.")
        if normalized_family == "lysis_enabled" and config.lysis_mode == "off":
            raise ValueError(f"Model `{model_type}` unexpectedly disabled lysis in lysis-enabled family.")


def regime_for_family(regime: RegimeConfig, family: ComparisonFamily) -> RegimeConfig:
    normalized_family = normalize_family(family)
    if normalized_family == "no_lysis":
        return replace(regime, lysis_mode="off")
    if regime.lysis_mode == "off":
        raise ValueError("lysis-enabled family requires a regime whose lysis_mode is not `off`.")
    return regime
