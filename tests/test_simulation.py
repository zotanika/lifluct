from lifluct.core.agents import ProposedTrade
from lifluct.core.simulation import SimulationRunner
from lifluct.baselines.dynamic_fee_single import run_dynamic_fee_single
from lifluct.baselines.static_cpmm import run_static_cpmm
from lifluct.baselines.lifluct_multi_cell import run_lifluct_multi_cell
from lifluct.reporting.loader import load_run_config
from lifluct.types import ClusterState, OracleState, RunConfig


def _base_config(**updates: object) -> RunConfig:
    raw = {
        "seed": 42,
        "num_steps": 50,
        "initial_reserve_a": 1_000.0,
        "initial_reserve_b": 100_000.0,
        "initial_price": 100.0,
        "sigma": 0.02,
        "q_trade": 0.35,
        "max_trade_fraction_of_tvl": 0.02,
        "arbitrage_threshold": 0.001,
        "baseline_type": "static_cpmm",
        "f_min": 0.003,
        "mu": 0.15,
        "tau": 0.002,
        "s_base": 1.0,
        "beta": 0.0,
        "tvl_target": 200_000.0,
        "oracle_mode": "perfect",
        "oracle_lag_steps": 0,
        "use_dynamic_fee": False,
        "use_turgor": False,
        "dt": 1.0,
        "oracle_observation_noise": 0.01,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def test_simulation_produces_trades_and_summary() -> None:
    result = run_static_cpmm(_base_config())

    assert result.summary.num_trades == len(result.trades)
    assert result.summary.num_trades > 0
    assert len(result.step_metrics) == result.config.num_steps + 1


def test_simulation_is_deterministic_under_seed() -> None:
    config = _base_config()
    result_one = run_dynamic_fee_single(config)
    result_two = run_dynamic_fee_single(config)

    assert result_one.summary.to_dict() == result_two.summary.to_dict()
    assert [trade.to_dict() for trade in result_one.trades] == [
        trade.to_dict() for trade in result_two.trades
    ]


def test_static_and_dynamic_baselines_both_run_end_to_end() -> None:
    static_result = run_static_cpmm(load_run_config("lifluct/configs/baseline_static.yaml"))
    dynamic_result = run_dynamic_fee_single(load_run_config("lifluct/configs/baseline_dynamic.yaml"))

    assert static_result.summary.num_trades > 0
    assert dynamic_result.summary.num_trades > 0
    assert static_result.summary.total_lp_fee_b >= 0.0
    assert dynamic_result.summary.total_lp_fee_b >= 0.0


def test_multi_cell_run_completes_and_creates_epoch_outputs() -> None:
    config = _base_config(
        baseline_type="lifluct_multi_cell",
        num_steps=30,
        epoch_length=10,
        num_cells=4,
        enable_evolution=True,
        use_dynamic_fee=True,
        use_turgor=True,
    )
    result = run_lifluct_multi_cell(config)

    assert result.summary.num_trades > 0
    assert len(result.epoch_summaries) == 3
    assert len(result.cell_snapshots) == 12


def test_multi_cell_run_is_deterministic_under_seed() -> None:
    config = _base_config(
        baseline_type="lifluct_multi_cell",
        num_steps=30,
        epoch_length=10,
        num_cells=4,
        enable_evolution=True,
        use_dynamic_fee=True,
        use_turgor=True,
    )
    result_one = run_lifluct_multi_cell(config)
    result_two = run_lifluct_multi_cell(config)

    assert result_one.summary.to_dict() == result_two.summary.to_dict()
    assert [summary.to_dict() for summary in result_one.epoch_summaries] == [
        summary.to_dict() for summary in result_two.epoch_summaries
    ]
    assert [snapshot.to_dict() for snapshot in result_one.cell_snapshots] == [
        snapshot.to_dict() for snapshot in result_two.cell_snapshots
    ]


def _integrity_config(**updates: object) -> RunConfig:
    raw = {
        "seed": 7,
        "num_steps": 1,
        "epoch_length": 1,
        "initial_reserve_a": 1_000.0,
        "initial_reserve_b": 100_000.0,
        "initial_price": 101.0,
        "sigma": 0.0,
        "q_trade": 0.0,
        "max_trade_fraction_of_tvl": 0.02,
        "arbitrage_threshold": 0.001,
        "baseline_type": "lifluct_multi_cell",
        "f_min": 0.50,
        "mu": 0.15,
        "tau": 0.002,
        "s_base": 1.0,
        "beta": 0.0,
        "tvl_target": 200_000.0,
        "oracle_mode": "perfect",
        "oracle_lag_steps": 0,
        "use_dynamic_fee": False,
        "use_turgor": False,
        "num_cells": 1,
        "enable_evolution": False,
        "toxic_trade_probability": 1.0,
        "num_toxic_attempts_per_step": 1,
        "toxic_mode": "cheapest_active",
        "lysis_mode": "off",
        "kappa": 3.0,
        "fee_max_global": 0.50,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def _cell_stats(cell) -> tuple[float, float, float, float, float, float, int, int, int, int]:
    return (
        cell.epoch_volume_b,
        cell.epoch_lp_revenue_b,
        cell.epoch_protocol_revenue_b,
        cell.epoch_trader_cost_b,
        cell.epoch_attributed_loss_b,
        cell.epoch_fees_total_b,
        cell.epoch_num_trades,
        cell.epoch_num_noise_trades,
        cell.epoch_num_arbitrage_trades,
        cell.lifetime_trades,
    )


def test_rejected_toxic_trade_does_not_mutate_cell_stats() -> None:
    runner = SimulationRunner(_integrity_config())
    state = ClusterState(1_000.0, 100_000.0)
    cell = runner._initialize_cells()[0]
    oracle_state = OracleState(true_price=101.0, observed_price=101.0, step=1)
    proposed_trade = ProposedTrade(actor_type="arbitrage", direction="b_to_a", amount_in=1_000.0)

    preview = runner._preview_trade(
        state=state,
        oracle_state=oracle_state,
        proposed_trade=proposed_trade,
        cell=cell,
    )
    before = _cell_stats(cell)
    new_state, trade_record, arbitrage_profit_b, lysis_increment = runner._process_trade(
        state=state,
        oracle_state=oracle_state,
        proposed_trade=proposed_trade,
        cell=cell,
        epoch_index=0,
        routing_mode="cheapest_active",
        require_positive_arbitrage=True,
    )

    assert preview.arbitrage_profit_b <= 0.0
    assert new_state == state
    assert trade_record is None
    assert arbitrage_profit_b <= 0.0
    assert lysis_increment == 0
    assert _cell_stats(cell) == before


def test_rejected_toxic_trade_does_not_trigger_lysis() -> None:
    runner = SimulationRunner(_integrity_config(f_min=0.01, lysis_mode="hard", kappa=5.0))
    state = ClusterState(1_000.0, 100_000.0)
    cell = runner._initialize_cells()[0]
    cell.epoch_fees_total_b = 10.0
    oracle_state = OracleState(true_price=95.0, observed_price=90.0, step=1)
    proposed_trade = ProposedTrade(actor_type="arbitrage", direction="b_to_a", amount_in=1_000.0)

    preview = runner._preview_trade(
        state=state,
        oracle_state=oracle_state,
        proposed_trade=proposed_trade,
        cell=cell,
    )
    _, trade_record, arbitrage_profit_b, _ = runner._process_trade(
        state=state,
        oracle_state=oracle_state,
        proposed_trade=proposed_trade,
        cell=cell,
        epoch_index=0,
        routing_mode="cheapest_active",
        require_positive_arbitrage=True,
    )

    assert preview.would_trigger_lysis is True
    assert arbitrage_profit_b <= 0.0
    assert trade_record is None
    assert cell.lysis_triggered is False
    assert cell.active is True
    assert cell.lifetime_lysis_count == 0


def test_rejected_toxic_trade_emits_no_trade_record() -> None:
    result = SimulationRunner(_integrity_config(lysis_mode="hard", kappa=0.05)).run_single()

    assert result.trades == []
    assert result.summary.num_trades == 0
    assert result.summary.num_arbitrage_trades == 0


def test_committed_toxic_trade_still_updates_everything() -> None:
    runner = SimulationRunner(
        _integrity_config(
            initial_price=120.0,
            f_min=0.003,
            fee_max_global=0.50,
            lysis_mode="hard",
            kappa=10.0,
        )
    )
    state = ClusterState(1_000.0, 100_000.0)
    cell = runner._initialize_cells()[0]
    oracle_state = OracleState(true_price=120.0, observed_price=120.0, step=1)
    proposed_trade = ProposedTrade(actor_type="arbitrage", direction="b_to_a", amount_in=1_000.0)

    preview = runner._preview_trade(
        state=state,
        oracle_state=oracle_state,
        proposed_trade=proposed_trade,
        cell=cell,
    )
    new_state, trade_record, arbitrage_profit_b, lysis_increment = runner._process_trade(
        state=state,
        oracle_state=oracle_state,
        proposed_trade=proposed_trade,
        cell=cell,
        epoch_index=0,
        routing_mode="cheapest_active",
        require_positive_arbitrage=True,
    )

    assert preview.arbitrage_profit_b > 0.0
    assert new_state != state
    assert trade_record is not None
    assert trade_record.actor_type == "arbitrage"
    assert arbitrage_profit_b > 0.0
    assert cell.epoch_volume_b > 0.0
    assert cell.epoch_lp_revenue_b > 0.0
    assert cell.epoch_attributed_loss_b > 0.0
    assert cell.epoch_num_arbitrage_trades == 1
    assert cell.lifetime_trades == 1
    assert cell.lysis_triggered is True
    assert cell.active is False
    assert lysis_increment == 1


def test_run_summary_uses_only_committed_trades() -> None:
    result = SimulationRunner(
        _integrity_config(
            initial_price=120.0,
            f_min=0.003,
            lysis_mode="off",
        )
    ).run_single()

    assert result.trades
    assert result.summary.total_lp_revenue_b == sum(trade.lp_fee_amount_b for trade in result.trades)
    assert result.summary.total_protocol_revenue_b == sum(
        trade.protocol_fee_amount_b for trade in result.trades
    )
    assert result.summary.total_attributed_loss_b == sum(
        trade.attributed_loss_b for trade in result.trades
    )
    assert result.summary.total_trader_cost_b == sum(trade.trader_cost_b for trade in result.trades)
    assert result.summary.num_trades == len(result.trades)


def test_epoch_summary_not_contaminated_by_rejected_candidates() -> None:
    result = SimulationRunner(
        _integrity_config(
            lysis_mode="hard",
            kappa=0.05,
        )
    ).run_single()

    assert len(result.epoch_summaries) == 1
    epoch_summary = result.epoch_summaries[0]
    assert epoch_summary.total_volume_b == 0.0
    assert epoch_summary.total_lp_revenue_b == 0.0
    assert epoch_summary.total_protocol_revenue_b == 0.0
    assert epoch_summary.total_attributed_loss_b == 0.0
    assert epoch_summary.total_trader_cost_b == 0.0
    assert epoch_summary.num_lysed_cells == 0
    assert result.cell_snapshots
    snapshot = result.cell_snapshots[0]
    assert snapshot.epoch_volume_b == 0.0
    assert snapshot.epoch_lp_revenue_b == 0.0
    assert snapshot.epoch_protocol_revenue_b == 0.0
    assert snapshot.epoch_attributed_loss_b == 0.0
    assert snapshot.lysis_triggered is False
