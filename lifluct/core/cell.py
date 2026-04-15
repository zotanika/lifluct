"""Cell policy state for the multi-cell LIFLUCT simulator."""

from __future__ import annotations

from dataclasses import dataclass

from lifluct.core.attribution import dynamic_fee, lp_share
from lifluct.types import CellSnapshot


@dataclass(slots=True)
class CellGenes:
    """
    Gene vector for one Cell policy.

    Economic meaning:
    - f_min: baseline fee
    - mu: oracle-deviation fee sensitivity
    - tau: tolerance band before fee escalation
    - beta: lifluct retention sensitivity
    """

    f_min: float
    mu: float
    tau: float
    beta: float

    def to_dict(self) -> dict[str, float]:
        return {
            "f_min": self.f_min,
            "mu": self.mu,
            "tau": self.tau,
            "beta": self.beta,
        }


@dataclass(slots=True)
class CellState:
    cell_id: int
    active: bool
    lysis_triggered: bool
    generation_index: int
    parent_cell_id: int | None
    genes: CellGenes
    weight_user_routing: float = 1.0
    epoch_volume_b: float = 0.0
    epoch_lp_revenue_b: float = 0.0
    epoch_protocol_revenue_b: float = 0.0
    epoch_trader_cost_b: float = 0.0
    epoch_attributed_loss_b: float = 0.0
    epoch_fees_total_b: float = 0.0
    epoch_num_trades: int = 0
    epoch_num_noise_trades: int = 0
    epoch_num_arbitrage_trades: int = 0
    rolling_fitness_mean: float | None = None
    rolling_fitness_std: float | None = None
    lifetime_trades: int = 0
    lifetime_lysis_count: int = 0
    lifetime_death_count: int = 0
    routing_weight_multiplier: float = 1.0

    def reset_epoch_stats(self) -> None:
        self.active = True
        self.lysis_triggered = False
        self.routing_weight_multiplier = 1.0
        self.epoch_volume_b = 0.0
        self.epoch_lp_revenue_b = 0.0
        self.epoch_protocol_revenue_b = 0.0
        self.epoch_trader_cost_b = 0.0
        self.epoch_attributed_loss_b = 0.0
        self.epoch_fees_total_b = 0.0
        self.epoch_num_trades = 0
        self.epoch_num_noise_trades = 0
        self.epoch_num_arbitrage_trades = 0

    def compute_fee(self, deviation_value: float, fee_max_global: float) -> float:
        return min(
            fee_max_global,
            dynamic_fee(
                f_min=self.genes.f_min,
                mu=self.genes.mu,
                tau=self.genes.tau,
                deviation_value=deviation_value,
            ),
        )

    def compute_lp_share(self, lifluct_pressure_value: float, s_base: float) -> float:
        return lp_share(
            s_base=s_base,
            beta=self.genes.beta,
            pressure=lifluct_pressure_value,
        )

    def current_user_routing_weight(self) -> float:
        return self.weight_user_routing * self.routing_weight_multiplier

    def record_trade(
        self,
        *,
        actor_type: str,
        volume_b: float,
        lp_revenue_b: float,
        protocol_revenue_b: float,
        trader_cost_b: float,
        attributed_loss_b: float,
    ) -> None:
        """
        Record one trade in asset-B numeraire.

        All cell-level accounting aggregates are kept in asset-B terms so fitness and
        reporting remain directly comparable across directions.
        """
        self.epoch_volume_b += volume_b
        self.epoch_lp_revenue_b += lp_revenue_b
        self.epoch_protocol_revenue_b += protocol_revenue_b
        self.epoch_trader_cost_b += trader_cost_b
        self.epoch_attributed_loss_b += attributed_loss_b
        self.epoch_fees_total_b += lp_revenue_b + protocol_revenue_b
        self.epoch_num_trades += 1
        self.lifetime_trades += 1
        if actor_type == "noise":
            self.epoch_num_noise_trades += 1
        elif actor_type == "arbitrage":
            self.epoch_num_arbitrage_trades += 1

    def snapshot(
        self,
        *,
        epoch_index: int,
        fitness: float,
        active_override: bool | None = None,
    ) -> CellSnapshot:
        return CellSnapshot(
            epoch_index=epoch_index,
            cell_id=self.cell_id,
            active=self.active if active_override is None else active_override,
            lysis_triggered=self.lysis_triggered,
            generation_index=self.generation_index,
            parent_cell_id=self.parent_cell_id,
            f_min=self.genes.f_min,
            mu=self.genes.mu,
            tau=self.genes.tau,
            beta=self.genes.beta,
            epoch_volume_b=self.epoch_volume_b,
            epoch_lp_revenue_b=self.epoch_lp_revenue_b,
            epoch_protocol_revenue_b=self.epoch_protocol_revenue_b,
            epoch_trader_cost_b=self.epoch_trader_cost_b,
            epoch_attributed_loss_b=self.epoch_attributed_loss_b,
            epoch_fees_total_b=self.epoch_fees_total_b,
            fitness=fitness,
        )
