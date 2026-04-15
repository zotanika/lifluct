"""Typed dataclasses shared across the LIFLUCT research simulator."""

from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Literal, Mapping

BaselineType = Literal[
    "static_cpmm",
    "dynamic_fee_single",
    "lifluct_multi_cell",
    "best_fixed_single_cell",
]
ComparisonFamily = Literal["no_lysis", "lysis_enabled"]
OracleMode = Literal["perfect", "lagged", "noisy"]
ActorType = Literal["noise", "arbitrage"]
TradeDirection = Literal["a_to_b", "b_to_a"]
RetentionMode = Literal["full_trace", "epoch_only", "summary_only", "hybrid_debug"]


@dataclass(slots=True)
class ClusterState:
    reserve_a: float
    reserve_b: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(slots=True)
class OracleState:
    true_price: float
    observed_price: float
    step: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(slots=True)
class TradeRecord:
    trade_id: int
    step: int
    actor_type: str
    direction: str
    amount_in: float
    amount_out: float
    notional_b: float
    exec_price: float
    oracle_price: float
    pool_price_before: float
    pool_price_after: float
    fee_rate: float
    lp_fee_amount_b: float
    protocol_fee_amount_b: float
    attributed_loss_b: float
    trader_cost_b: float
    epoch_index: int = 0
    routing_mode: str = ""
    cell_id: int | None = None

    def to_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


@dataclass(slots=True)
class RunSummary:
    final_lp_value_b: float
    final_hodl_value_b: float
    lp_minus_hodl_b: float
    total_lp_revenue_b: float
    total_protocol_revenue_b: float
    total_lp_fee_b: float
    total_protocol_fee_b: float
    total_attributed_loss_b: float
    total_trader_cost_b: float
    total_arbitrage_profit_b: float
    num_trades: int
    num_noise_trades: int
    num_arbitrage_trades: int
    total_lysis_count: int = 0
    total_dead_cells: int = 0

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class RunConfig:
    seed: int
    num_steps: int
    initial_reserve_a: float
    initial_reserve_b: float
    initial_price: float
    sigma: float
    q_trade: float
    max_trade_fraction_of_tvl: float
    arbitrage_threshold: float
    baseline_type: str
    f_min: float
    mu: float
    tau: float
    s_base: float
    beta: float
    tvl_target: float
    oracle_mode: str
    oracle_lag_steps: int
    use_dynamic_fee: bool
    use_turgor: bool
    attribution_mode: str = "observed_spot"
    attribution_lag_steps: int = 1
    attribution_twap_window: int = 5
    delayed_reference_steps: int = 1
    research_future_horizon: int = 3
    dt: float = 1.0
    oracle_observation_noise: float = 0.01
    num_cells: int = 1
    epoch_length: int = 100
    user_routing_mode: str = "weighted_random"
    toxic_routing_mode: str = "cheapest_active"
    toxic_mode: str = ""
    p_best: float = 0.8
    toxic_trade_probability: float = 1.0
    num_toxic_attempts_per_step: int = 1
    toxic_burst_probability: float = 1.0
    toxic_burst_start_step: int = 0
    toxic_burst_end_step: int = 0
    sabotage_target_cell_mode: str = "weakest_fitness"
    sabotage_target_cell_id: int = -1
    fee_max_global: float = 0.5
    fitness_mode: str = "basic_normalized"
    fitness_lambda: float = 1.0
    fitness_gamma: float = 1.0
    fitness_omega: float = 1.0
    min_volume_threshold: float = 0.0
    inactivity_penalty: float = 0.0
    selection_fraction: float = 0.5
    mutation_mode: str = "multiplicative_gaussian"
    mutation_sigma_f_min: float = 0.10
    mutation_sigma_mu: float = 0.10
    mutation_sigma_tau: float = 0.10
    mutation_sigma_beta: float = 0.10
    elite_count: int = 0
    parent_selection_mode: str = "uniform"
    enable_evolution: bool = False
    lysis_mode: str = "off"
    kappa: float = 3.0
    soft_lysis_penalty: float = 0.05
    f_min_min: float = 0.0005
    f_min_max: float = 0.01
    mu_min: float = 0.0
    mu_max: float = 25.0
    tau_min: float = 0.0001
    tau_max: float = 0.02
    beta_min: float = 0.0
    beta_max: float = 5.0
    gene_init_f_min_min: float = 0.0005
    gene_init_f_min_max: float = 0.005
    gene_init_mu_min: float = 0.1
    gene_init_mu_max: float = 5.0
    gene_init_tau_min: float = 0.0005
    gene_init_tau_max: float = 0.005
    gene_init_beta_min: float = 0.0
    gene_init_beta_max: float = 1.0
    epsilon: float = 1e-12

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RunConfig":
        allowed = {field.name for field in fields(cls)}
        cleaned = {key: value for key, value in raw.items() if key in allowed}
        if cleaned.get("lysis_mode") is False:
            cleaned["lysis_mode"] = "off"
        elif cleaned.get("lysis_mode") is True:
            cleaned["lysis_mode"] = "hard"
        return cls(**cleaned)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class RegimeConfig:
    """
    Environment definition for fair model comparisons.

    A regime is the part of a run that should stay fixed across models when we ask
    "regime x model" questions. Model-specific strategy knobs such as Cell count,
    evolution, and gene values are intentionally excluded.
    """

    seed: int
    num_steps: int
    initial_reserve_a: float
    initial_reserve_b: float
    initial_price: float
    tvl_target: float
    sigma: float
    dt: float
    oracle_mode: str
    oracle_lag_steps: int
    oracle_observation_noise: float
    attribution_mode: str
    attribution_lag_steps: int
    attribution_twap_window: int
    delayed_reference_steps: int
    research_future_horizon: int
    q_trade: float
    max_trade_fraction_of_tvl: float
    arbitrage_threshold: float
    epoch_length: int
    user_routing_mode: str
    toxic_routing_mode: str
    toxic_mode: str
    p_best: float
    toxic_trade_probability: float
    num_toxic_attempts_per_step: int
    toxic_burst_probability: float
    toxic_burst_start_step: int
    toxic_burst_end_step: int
    sabotage_target_cell_mode: str
    sabotage_target_cell_id: int
    fee_max_global: float
    lysis_mode: str
    kappa: float
    soft_lysis_penalty: float

    @classmethod
    def from_run_config(cls, config: RunConfig) -> "RegimeConfig":
        return cls(
            seed=config.seed,
            num_steps=config.num_steps,
            initial_reserve_a=config.initial_reserve_a,
            initial_reserve_b=config.initial_reserve_b,
            initial_price=config.initial_price,
            tvl_target=config.tvl_target,
            sigma=config.sigma,
            dt=config.dt,
            oracle_mode=config.oracle_mode,
            oracle_lag_steps=config.oracle_lag_steps,
            oracle_observation_noise=config.oracle_observation_noise,
            attribution_mode=config.attribution_mode,
            attribution_lag_steps=config.attribution_lag_steps,
            attribution_twap_window=config.attribution_twap_window,
            delayed_reference_steps=config.delayed_reference_steps,
            research_future_horizon=config.research_future_horizon,
            q_trade=config.q_trade,
            max_trade_fraction_of_tvl=config.max_trade_fraction_of_tvl,
            arbitrage_threshold=config.arbitrage_threshold,
            epoch_length=config.epoch_length,
            user_routing_mode=config.user_routing_mode,
            toxic_routing_mode=config.toxic_routing_mode,
            toxic_mode=config.toxic_mode or config.toxic_routing_mode,
            p_best=config.p_best,
            toxic_trade_probability=config.toxic_trade_probability,
            num_toxic_attempts_per_step=config.num_toxic_attempts_per_step,
            toxic_burst_probability=config.toxic_burst_probability,
            toxic_burst_start_step=config.toxic_burst_start_step,
            toxic_burst_end_step=config.toxic_burst_end_step,
            sabotage_target_cell_mode=config.sabotage_target_cell_mode,
            sabotage_target_cell_id=config.sabotage_target_cell_id,
            fee_max_global=config.fee_max_global,
            lysis_mode=config.lysis_mode,
            kappa=config.kappa,
            soft_lysis_penalty=config.soft_lysis_penalty,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def regime_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"regime_{digest[:12]}"

    def to_run_overrides(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass(slots=True)
class StepMetric:
    step: int
    true_price: float
    observed_price: float
    pool_price: float
    reserve_a: float
    reserve_b: float
    tvl_b: float
    lp_value_b: float
    hodl_value_b: float
    cumulative_lp_fee_b: float
    cumulative_protocol_fee_b: float
    cumulative_attributed_loss_b: float
    cumulative_trader_cost_b: float
    cumulative_arbitrage_profit_b: float
    num_trades: int
    epoch_index: int = 0
    num_active_cells: int = 1
    num_lysed_cells: int = 0

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(slots=True)
class EpochSummary:
    epoch_index: int
    num_active_cells: int
    num_lysed_cells: int
    num_dead_cells: int
    mean_fitness: float
    median_fitness: float
    total_lp_revenue_b: float
    total_protocol_revenue_b: float
    total_attributed_loss_b: float
    total_trader_cost_b: float
    total_volume_b: float
    avg_fee_rate: float
    top_cell_ids: list[int]
    top_cell_gene_summary: str

    def to_dict(self) -> dict[str, float | int | str]:
        payload = asdict(self)
        payload["top_cell_ids"] = json.dumps(self.top_cell_ids)
        return payload


@dataclass(slots=True)
class CellSnapshot:
    epoch_index: int
    cell_id: int
    active: bool
    lysis_triggered: bool
    generation_index: int
    parent_cell_id: int | None
    f_min: float
    mu: float
    tau: float
    beta: float
    epoch_volume_b: float
    epoch_lp_revenue_b: float
    epoch_protocol_revenue_b: float
    epoch_trader_cost_b: float
    epoch_attributed_loss_b: float
    epoch_fees_total_b: float
    fitness: float

    def to_dict(self) -> dict[str, float | int | bool | None]:
        return asdict(self)


@dataclass(slots=True)
class ValidationWarning:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class FailureModeObservation:
    mode: str
    severity: str
    evidence: str
    trigger_heuristic: str = ""
    evidence_fields: dict[str, Any] = field(default_factory=dict)
    is_heuristic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RegistryRecord:
    experiment_id: str
    run_id: str
    config_hash: str
    regime_id: str
    seed: int
    timestamp: str
    model_type: str
    model_family: str
    baseline_type: str
    label: str
    attribution_mode: str
    toxic_mode: str
    lysis_mode: str
    fitness_mode: str
    run_dir: str
    final_lp_minus_hodl_b: float
    lp_minus_hodl_b: float
    total_attributed_loss_b: float
    total_lp_revenue_b: float
    total_trader_cost_b: float
    total_arbitrage_profit_b: float
    total_lysis_count: int
    total_dead_cells: int
    final_active_cells: int
    gene_dispersion_final: float
    detected_failure_modes: str
    warnings_count: int
    failure_modes_count: int
    experiment_family: str = ""
    retention_mode: str = "full_trace"
    dominant_cell_concentration_final: float = 0.0

    def to_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


@dataclass(slots=True)
class SimulationResult:
    config: RunConfig
    final_state: ClusterState
    trades: list[TradeRecord]
    step_metrics: list[StepMetric]
    summary: RunSummary
    epoch_summaries: list[EpochSummary] = field(default_factory=list)
    cell_snapshots: list[CellSnapshot] = field(default_factory=list)
    validation_warnings: list[ValidationWarning] = field(default_factory=list)
    failure_modes: list[FailureModeObservation] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "final_state": self.final_state.to_dict(),
            "trades": [trade.to_dict() for trade in self.trades],
            "step_metrics": [metric.to_dict() for metric in self.step_metrics],
            "summary": self.summary.to_dict(),
            "epoch_summaries": [summary.to_dict() for summary in self.epoch_summaries],
            "cell_snapshots": [snapshot.to_dict() for snapshot in self.cell_snapshots],
            "validation_warnings": [warning.to_dict() for warning in self.validation_warnings],
            "failure_modes": [mode.to_dict() for mode in self.failure_modes],
            "diagnostics": dict(self.diagnostics),
        }
