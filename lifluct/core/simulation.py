"""Simulation runner for Phase 1 baselines and Phase 2 multi-cell LIFLUCT."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

import numpy as np

from lifluct.core.agents import ProposedTrade, build_arbitrage_trade, generate_noise_trade
from lifluct.core.adversaries import choose_adversarial_cell, toxic_flow_probability
from lifluct.core.attribution import (
    attributed_loss_b,
    deviation,
    trader_cost_proxy_b,
    lifluct_pressure,
)
from lifluct.core.cell import CellGenes, CellState
from lifluct.core.cluster import pool_price, swap_a_to_b, swap_b_to_a, tvl
from lifluct.core.evolution import advance_generation, compute_fitness_for_cells, rank_cells, select_survivors
from lifluct.core.lysis import apply_lysis
from lifluct.core.oracle import OracleProcess
from lifluct.core.routing import choose_user_cell
from lifluct.types import (
    ClusterState,
    EpochSummary,
    OracleState,
    RunConfig,
    RunSummary,
    SimulationResult,
    StepMetric,
    TradeRecord,
)


@dataclass(slots=True)
class TradePreview:
    """
    Pure trade preview used to keep execution atomic.

    Preview computes the candidate post-trade state and all accounting values, but
    it does not mutate Cell state, lysis state, cumulative totals, or trade logs.
    """

    candidate_state: ClusterState
    proposed_trade: ProposedTrade
    oracle_step: int
    oracle_price_observed: float
    amount_out: float
    notional_b: float
    exec_price: float
    pool_price_before: float
    pool_price_after: float
    fee_rate: float
    lp_fee_amount_b: float
    protocol_fee_amount_b: float
    total_fee_amount_b: float
    attributed_loss_b: float
    trader_cost_b: float
    arbitrage_profit_b: float
    would_trigger_lysis: bool


class SimulationRunner:
    """Deterministic shared-cluster simulator for the LIFLUCT research repository."""

    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.trade_rng = np.random.default_rng(config.seed + 1_000_000)
        self.population_rng = np.random.default_rng(config.seed + 2_000_000)
        self.evolution_rng = np.random.default_rng(config.seed + 3_000_000)
        self.trade_id = 0

    def run(self) -> SimulationResult:
        return self.run_single()

    def run_single(self) -> SimulationResult:
        state = ClusterState(
            reserve_a=self.config.initial_reserve_a,
            reserve_b=self.config.initial_reserve_b,
        )
        cells = self._initialize_cells()
        oracle = OracleProcess(self.config)
        oracle_state = oracle.current()

        trades: list[TradeRecord] = []
        step_metrics: list[StepMetric] = []
        epoch_summaries: list[EpochSummary] = []
        cell_snapshots = []
        epoch_trade_records: list[TradeRecord] = []

        cumulative_lp_fee_b = 0.0
        cumulative_protocol_fee_b = 0.0
        cumulative_attributed_loss_b = 0.0
        cumulative_trader_cost_b = 0.0
        cumulative_arbitrage_profit_b = 0.0
        total_lysis_count = 0
        total_dead_cells = 0
        num_noise_trades = 0
        num_arbitrage_trades = 0
        epoch_index = 0

        step_metrics.append(
            self._build_step_metric(
                step=0,
                epoch_index=epoch_index,
                state=state,
                oracle_state=oracle_state,
                cells=cells,
                cumulative_lp_fee_b=cumulative_lp_fee_b,
                cumulative_protocol_fee_b=cumulative_protocol_fee_b,
                cumulative_attributed_loss_b=cumulative_attributed_loss_b,
                cumulative_trader_cost_b=cumulative_trader_cost_b,
                cumulative_arbitrage_profit_b=cumulative_arbitrage_profit_b,
                num_trades=0,
            )
        )

        for step in range(1, self.config.num_steps + 1):
            oracle_state = oracle.step()

            maybe_noise_trade = generate_noise_trade(
                rng=self.trade_rng,
                q_trade=self.config.q_trade,
                state=state,
                oracle_price=oracle_state.true_price,
                max_trade_fraction_of_tvl=self.config.max_trade_fraction_of_tvl,
            )
            if maybe_noise_trade is not None:
                fee_map = self._build_fee_map(cells, state, oracle_state)
                user_cell = choose_user_cell(
                    cells=cells,
                    routing_mode=self.config.user_routing_mode,
                    current_fee_map=fee_map,
                    rng=self.trade_rng,
                    p_best=self.config.p_best,
                )
                if user_cell is not None:
                    state, trade_record, arbitrage_profit_b, lysis_increment = self._process_trade(
                        state=state,
                        oracle_state=oracle_state,
                        proposed_trade=maybe_noise_trade,
                        cell=user_cell,
                        epoch_index=epoch_index,
                        routing_mode=self.config.user_routing_mode,
                        require_positive_arbitrage=False,
                    )
                    if trade_record is None:
                        continue
                    trades.append(trade_record)
                    epoch_trade_records.append(trade_record)
                    cumulative_lp_fee_b += trade_record.lp_fee_amount_b
                    cumulative_protocol_fee_b += trade_record.protocol_fee_amount_b
                    cumulative_attributed_loss_b += trade_record.attributed_loss_b
                    cumulative_trader_cost_b += trade_record.trader_cost_b
                    cumulative_arbitrage_profit_b += arbitrage_profit_b
                    total_lysis_count += lysis_increment
                    num_noise_trades += 1

            for _ in range(self.config.num_toxic_attempts_per_step):
                if self.trade_rng.random() > toxic_flow_probability(self.config, step):
                    continue
                fee_map = self._build_fee_map(cells, state, oracle_state)
                toxic_cell = choose_adversarial_cell(
                    cells=cells,
                    current_fee_map=fee_map,
                    rng=self.trade_rng,
                    config=self.config,
                    state=state,
                    oracle_state=oracle_state,
                )
                if toxic_cell is None:
                    continue
                maybe_arb_trade = build_arbitrage_trade(
                    state=state,
                    oracle_price=oracle_state.true_price,
                    fee_rate=fee_map[toxic_cell.cell_id],
                    arbitrage_threshold=self.config.arbitrage_threshold,
                )
                if maybe_arb_trade is None:
                    continue
                state, trade_record, arbitrage_profit_b, lysis_increment = self._process_trade(
                    state=state,
                    oracle_state=oracle_state,
                    proposed_trade=maybe_arb_trade,
                    cell=toxic_cell,
                    epoch_index=epoch_index,
                    routing_mode=self.config.toxic_mode or self.config.toxic_routing_mode,
                    require_positive_arbitrage=True,
                )
                if trade_record is None:
                    continue
                trades.append(trade_record)
                epoch_trade_records.append(trade_record)
                cumulative_lp_fee_b += trade_record.lp_fee_amount_b
                cumulative_protocol_fee_b += trade_record.protocol_fee_amount_b
                cumulative_attributed_loss_b += trade_record.attributed_loss_b
                cumulative_trader_cost_b += trade_record.trader_cost_b
                cumulative_arbitrage_profit_b += arbitrage_profit_b
                total_lysis_count += lysis_increment
                num_arbitrage_trades += 1

            step_metrics.append(
                self._build_step_metric(
                    step=step,
                    epoch_index=epoch_index,
                    state=state,
                    oracle_state=oracle_state,
                    cells=cells,
                    cumulative_lp_fee_b=cumulative_lp_fee_b,
                    cumulative_protocol_fee_b=cumulative_protocol_fee_b,
                    cumulative_attributed_loss_b=cumulative_attributed_loss_b,
                    cumulative_trader_cost_b=cumulative_trader_cost_b,
                    cumulative_arbitrage_profit_b=cumulative_arbitrage_profit_b,
                    num_trades=len(trades),
                )
            )

            if step % self.config.epoch_length == 0 or step == self.config.num_steps:
                (
                    cells,
                    epoch_summary,
                    snapshots,
                    dead_count,
                ) = self._roll_epoch(
                    epoch_index=epoch_index,
                    cells=cells,
                    epoch_trade_records=epoch_trade_records,
                )
                epoch_summaries.append(epoch_summary)
                cell_snapshots.extend(snapshots)
                total_dead_cells += dead_count
                epoch_trade_records = []
                epoch_index += 1

        final_true_price = oracle_state.true_price
        final_lp_value_b = state.reserve_a * final_true_price + state.reserve_b
        final_hodl_value_b = (
            self.config.initial_reserve_a * final_true_price + self.config.initial_reserve_b
        )
        summary = RunSummary(
            final_lp_value_b=final_lp_value_b,
            final_hodl_value_b=final_hodl_value_b,
            lp_minus_hodl_b=final_lp_value_b - final_hodl_value_b,
            total_lp_revenue_b=cumulative_lp_fee_b,
            total_protocol_revenue_b=cumulative_protocol_fee_b,
            total_lp_fee_b=cumulative_lp_fee_b,
            total_protocol_fee_b=cumulative_protocol_fee_b,
            total_attributed_loss_b=cumulative_attributed_loss_b,
            total_trader_cost_b=cumulative_trader_cost_b,
            total_arbitrage_profit_b=cumulative_arbitrage_profit_b,
            num_trades=len(trades),
            num_noise_trades=num_noise_trades,
            num_arbitrage_trades=num_arbitrage_trades,
            total_lysis_count=total_lysis_count,
            total_dead_cells=total_dead_cells,
        )
        return SimulationResult(
            config=self.config,
            final_state=state,
            trades=trades,
            step_metrics=step_metrics,
            summary=summary,
            epoch_summaries=epoch_summaries,
            cell_snapshots=cell_snapshots,
        )

    def run_many(self, configs: list[RunConfig]) -> list[SimulationResult]:
        return [SimulationRunner(config).run_single() for config in configs]

    def with_overrides(self, **updates: object) -> "SimulationRunner":
        return SimulationRunner(replace(self.config, **updates))

    def _initialize_cells(self) -> list[CellState]:
        if self.config.num_cells <= 1 or self.config.baseline_type in {"static_cpmm", "dynamic_fee_single"}:
            return [
                CellState(
                    cell_id=0,
                    active=True,
                    lysis_triggered=False,
                    generation_index=0,
                    parent_cell_id=None,
                    genes=CellGenes(
                        f_min=self.config.f_min,
                        mu=self.config.mu,
                        tau=self.config.tau,
                        beta=self.config.beta,
                    ),
                    weight_user_routing=1.0,
                )
            ]

        cells: list[CellState] = []
        for cell_id in range(self.config.num_cells):
            cells.append(
                CellState(
                    cell_id=cell_id,
                    active=True,
                    lysis_triggered=False,
                    generation_index=0,
                    parent_cell_id=None,
                    genes=CellGenes(
                        f_min=float(
                            self.population_rng.uniform(
                                self.config.gene_init_f_min_min,
                                self.config.gene_init_f_min_max,
                            )
                        ),
                        mu=float(
                            self.population_rng.uniform(
                                self.config.gene_init_mu_min,
                                self.config.gene_init_mu_max,
                            )
                        ),
                        tau=float(
                            self.population_rng.uniform(
                                self.config.gene_init_tau_min,
                                self.config.gene_init_tau_max,
                            )
                        ),
                        beta=float(
                            self.population_rng.uniform(
                                self.config.gene_init_beta_min,
                                self.config.gene_init_beta_max,
                            )
                        ),
                    ),
                    weight_user_routing=1.0,
                )
            )
        return cells

    def _build_fee_map(
        self,
        cells: list[CellState],
        state: ClusterState,
        oracle_state: OracleState,
    ) -> dict[int, float]:
        current_deviation = deviation(
            pool_price=pool_price(state),
            oracle_price=oracle_state.observed_price,
        )
        fee_map: dict[int, float] = {}
        for cell in cells:
            if not cell.active:
                continue
            if not self.config.use_dynamic_fee:
                fee_map[cell.cell_id] = min(self.config.fee_max_global, cell.genes.f_min)
            else:
                fee_map[cell.cell_id] = cell.compute_fee(
                    deviation_value=current_deviation,
                    fee_max_global=self.config.fee_max_global,
                )
        return fee_map

    def _preview_trade(
        self,
        *,
        state: ClusterState,
        oracle_state: OracleState,
        proposed_trade: ProposedTrade,
        cell: CellState,
    ) -> TradePreview:
        deviation_value = deviation(
            pool_price=pool_price(state),
            oracle_price=oracle_state.observed_price,
        )
        fee_rate = (
            min(self.config.fee_max_global, cell.genes.f_min)
            if not self.config.use_dynamic_fee
            else cell.compute_fee(deviation_value, self.config.fee_max_global)
        )
        pressure_value = 0.0
        if self.config.use_turgor:
            pressure_value = lifluct_pressure(
                tvl=tvl(state, oracle_state.observed_price),
                tvl_target=self.config.tvl_target,
            )
        lp_share_value = cell.compute_lp_share(pressure_value, self.config.s_base)

        if proposed_trade.direction == "a_to_b":
            new_state, execution = swap_a_to_b(
                state=state,
                amount_in_a=proposed_trade.amount_in,
                fee_rate=fee_rate,
                lp_share_value=lp_share_value,
            )
            notional_b = proposed_trade.amount_in * oracle_state.observed_price
            lp_fee_b = execution.lp_fee_amount_in * oracle_state.observed_price
            protocol_fee_b = execution.protocol_fee_amount_in * oracle_state.observed_price
            total_fee_b = execution.total_fee_amount_in * oracle_state.observed_price
            arbitrage_profit_b = (
                execution.amount_out - proposed_trade.amount_in * oracle_state.true_price
                if proposed_trade.actor_type == "arbitrage"
                else 0.0
            )
        else:
            new_state, execution = swap_b_to_a(
                state=state,
                amount_in_b=proposed_trade.amount_in,
                fee_rate=fee_rate,
                lp_share_value=lp_share_value,
            )
            notional_b = proposed_trade.amount_in
            lp_fee_b = execution.lp_fee_amount_in
            protocol_fee_b = execution.protocol_fee_amount_in
            total_fee_b = execution.total_fee_amount_in
            arbitrage_profit_b = (
                execution.amount_out * oracle_state.true_price - proposed_trade.amount_in
                if proposed_trade.actor_type == "arbitrage"
                else 0.0
            )

        attributed_loss_value_b = attributed_loss_b(
            exec_price=execution.exec_price,
            oracle_price=oracle_state.observed_price,
            volume_b=notional_b,
            fee_rate=fee_rate,
        )
        trader_cost_value_b = trader_cost_proxy_b(
            exec_price=execution.exec_price,
            oracle_price=oracle_state.observed_price,
            volume_b=notional_b,
            fee_rate=fee_rate,
            fee_amount_b=total_fee_b,
        )

        return TradePreview(
            candidate_state=new_state,
            proposed_trade=proposed_trade,
            oracle_step=oracle_state.step,
            oracle_price_observed=oracle_state.observed_price,
            amount_out=execution.amount_out,
            notional_b=notional_b,
            exec_price=execution.exec_price,
            pool_price_before=execution.pool_price_before,
            pool_price_after=execution.pool_price_after,
            fee_rate=fee_rate,
            lp_fee_amount_b=lp_fee_b,
            protocol_fee_amount_b=protocol_fee_b,
            total_fee_amount_b=total_fee_b,
            attributed_loss_b=attributed_loss_value_b,
            trader_cost_b=trader_cost_value_b,
            arbitrage_profit_b=arbitrage_profit_b,
            would_trigger_lysis=self._would_trigger_lysis_after_trade(
                cell=cell,
                attributed_loss_b=attributed_loss_value_b,
                total_fee_b=total_fee_b,
            ),
        )

    def _commit_trade(
        self,
        *,
        preview: TradePreview,
        cell: CellState,
        epoch_index: int,
        routing_mode: str,
    ) -> tuple[ClusterState, TradeRecord, float, int]:
        cell.record_trade(
            actor_type=preview.proposed_trade.actor_type,
            volume_b=preview.notional_b,
            lp_revenue_b=preview.lp_fee_amount_b,
            protocol_revenue_b=preview.protocol_fee_amount_b,
            trader_cost_b=preview.trader_cost_b,
            attributed_loss_b=preview.attributed_loss_b,
        )

        lysis_increment = 0
        if preview.would_trigger_lysis and self.config.lysis_mode != "off":
            was_lysed = cell.lysis_triggered
            apply_lysis(
                cell,
                lysis_mode=self.config.lysis_mode,
                soft_penalty=self.config.soft_lysis_penalty,
            )
            if not was_lysed and cell.lysis_triggered:
                lysis_increment = 1

        trade_record = TradeRecord(
            trade_id=self.trade_id,
            step=preview.oracle_step,
            actor_type=preview.proposed_trade.actor_type,
            direction=preview.proposed_trade.direction,
            amount_in=preview.proposed_trade.amount_in,
            amount_out=preview.amount_out,
            notional_b=preview.notional_b,
            exec_price=preview.exec_price,
            oracle_price=preview.oracle_price_observed,
            pool_price_before=preview.pool_price_before,
            pool_price_after=preview.pool_price_after,
            fee_rate=preview.fee_rate,
            lp_fee_amount_b=preview.lp_fee_amount_b,
            protocol_fee_amount_b=preview.protocol_fee_amount_b,
            attributed_loss_b=preview.attributed_loss_b,
            trader_cost_b=preview.trader_cost_b,
            epoch_index=epoch_index,
            routing_mode=routing_mode,
            cell_id=cell.cell_id,
        )
        self.trade_id += 1
        return preview.candidate_state, trade_record, preview.arbitrage_profit_b, lysis_increment

    def _process_trade(
        self,
        *,
        state: ClusterState,
        oracle_state: OracleState,
        proposed_trade: ProposedTrade,
        cell: CellState,
        epoch_index: int,
        routing_mode: str,
        require_positive_arbitrage: bool,
    ) -> tuple[ClusterState, TradeRecord | None, float, int]:
        preview = self._preview_trade(
            state=state,
            oracle_state=oracle_state,
            proposed_trade=proposed_trade,
            cell=cell,
        )
        if require_positive_arbitrage and preview.arbitrage_profit_b <= 0.0:
            return state, None, preview.arbitrage_profit_b, 0
        return self._commit_trade(
            preview=preview,
            cell=cell,
            epoch_index=epoch_index,
            routing_mode=routing_mode,
        )

    def _would_trigger_lysis_after_trade(
        self,
        *,
        cell: CellState,
        attributed_loss_b: float,
        total_fee_b: float,
    ) -> bool:
        """
        Evaluate lysis on projected post-trade totals without mutating the Cell.

        This keeps preview side-effect-free so rejected toxic candidates cannot
        contaminate accounting or circuit-breaker state.
        """
        if self.config.lysis_mode == "off" or cell.lysis_triggered:
            return False
        projected_loss_b = cell.epoch_attributed_loss_b + attributed_loss_b
        projected_fees_b = cell.epoch_fees_total_b + total_fee_b
        return projected_loss_b > self.config.kappa * projected_fees_b

    def _roll_epoch(
        self,
        *,
        epoch_index: int,
        cells: list[CellState],
        epoch_trade_records: list[TradeRecord],
    ) -> tuple[list[CellState], EpochSummary, list, int]:
        fitness_map = compute_fitness_for_cells(cells, self.config)
        ranked_cells = rank_cells(cells, fitness_map)
        survivors, dead_cells = select_survivors(
            cells,
            fitness_map,
            selection_fraction=self.config.selection_fraction if self.config.enable_evolution else 1.0,
            elite_count=self.config.elite_count if self.config.enable_evolution else len(cells),
        )
        dead_ids = {cell.cell_id for cell in dead_cells}

        snapshots = [
            cell.snapshot(
                epoch_index=epoch_index,
                fitness=fitness_map[cell.cell_id],
                active_override=(cell.cell_id not in dead_ids and cell.active),
            )
            for cell in cells
        ]
        epoch_summary = self._build_epoch_summary(
            epoch_index=epoch_index,
            cells=cells,
            ranked_cells=ranked_cells,
            fitness_map=fitness_map,
            epoch_trade_records=epoch_trade_records,
            dead_cells=dead_cells,
        )

        if self.config.enable_evolution and len(cells) > 1:
            next_cells, _, _, dead_cells_after = advance_generation(
                cells,
                self.config,
                self.evolution_rng,
            )
            return next_cells, epoch_summary, snapshots, len(dead_cells_after)

        for cell in cells:
            cell.reset_epoch_stats()
        return cells, epoch_summary, snapshots, 0

    def _build_epoch_summary(
        self,
        *,
        epoch_index: int,
        cells: list[CellState],
        ranked_cells: list[CellState],
        fitness_map: dict[int, float],
        epoch_trade_records: list[TradeRecord],
        dead_cells: list[CellState],
    ) -> EpochSummary:
        top_cells = ranked_cells[: min(3, len(ranked_cells))]
        top_gene_payload = [
            {
                "cell_id": cell.cell_id,
                "fitness": fitness_map[cell.cell_id],
                "genes": cell.genes.to_dict(),
            }
            for cell in top_cells
        ]
        total_volume_b = sum(cell.epoch_volume_b for cell in cells)
        avg_fee_rate = 0.0
        if epoch_trade_records:
            weighted_fee = sum(record.fee_rate * record.notional_b for record in epoch_trade_records)
            total_notional = sum(record.notional_b for record in epoch_trade_records)
            avg_fee_rate = weighted_fee / total_notional if total_notional > 0 else 0.0

        return EpochSummary(
            epoch_index=epoch_index,
            num_active_cells=sum(1 for cell in cells if cell.active),
            num_lysed_cells=sum(1 for cell in cells if cell.lysis_triggered),
            num_dead_cells=len(dead_cells),
            mean_fitness=float(np.mean(list(fitness_map.values()))) if fitness_map else 0.0,
            median_fitness=float(np.median(list(fitness_map.values()))) if fitness_map else 0.0,
            total_lp_revenue_b=sum(cell.epoch_lp_revenue_b for cell in cells),
            total_protocol_revenue_b=sum(cell.epoch_protocol_revenue_b for cell in cells),
            total_attributed_loss_b=sum(cell.epoch_attributed_loss_b for cell in cells),
            total_trader_cost_b=sum(cell.epoch_trader_cost_b for cell in cells),
            total_volume_b=total_volume_b,
            avg_fee_rate=avg_fee_rate,
            top_cell_ids=[cell.cell_id for cell in top_cells],
            top_cell_gene_summary=json.dumps(top_gene_payload),
        )

    def _build_step_metric(
        self,
        *,
        step: int,
        epoch_index: int,
        state: ClusterState,
        oracle_state: OracleState,
        cells: list[CellState],
        cumulative_lp_fee_b: float,
        cumulative_protocol_fee_b: float,
        cumulative_attributed_loss_b: float,
        cumulative_trader_cost_b: float,
        cumulative_arbitrage_profit_b: float,
        num_trades: int,
    ) -> StepMetric:
        lp_value_b = state.reserve_a * oracle_state.true_price + state.reserve_b
        hodl_value_b = self.config.initial_reserve_a * oracle_state.true_price + self.config.initial_reserve_b
        return StepMetric(
            step=step,
            true_price=oracle_state.true_price,
            observed_price=oracle_state.observed_price,
            pool_price=pool_price(state),
            reserve_a=state.reserve_a,
            reserve_b=state.reserve_b,
            tvl_b=tvl(state, oracle_state.true_price),
            lp_value_b=lp_value_b,
            hodl_value_b=hodl_value_b,
            cumulative_lp_fee_b=cumulative_lp_fee_b,
            cumulative_protocol_fee_b=cumulative_protocol_fee_b,
            cumulative_attributed_loss_b=cumulative_attributed_loss_b,
            cumulative_trader_cost_b=cumulative_trader_cost_b,
            cumulative_arbitrage_profit_b=cumulative_arbitrage_profit_b,
            num_trades=num_trades,
            epoch_index=epoch_index,
            num_active_cells=sum(1 for cell in cells if cell.active),
            num_lysed_cells=sum(1 for cell in cells if cell.lysis_triggered),
        )
