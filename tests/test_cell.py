import pytest

from lifluct.core.cell import CellGenes, CellState


def _cell() -> CellState:
    return CellState(
        cell_id=0,
        active=True,
        lysis_triggered=False,
        generation_index=0,
        parent_cell_id=None,
        genes=CellGenes(f_min=0.003, mu=0.2, tau=0.002, beta=0.4),
    )


def test_cell_fee_calculation() -> None:
    cell = _cell()
    assert cell.compute_fee(0.01, fee_max_global=0.5) == pytest.approx(0.003 + 0.2 * 0.008)


def test_lp_share_calculation() -> None:
    cell = _cell()
    assert cell.compute_lp_share(lifluct_pressure_value=0.1, s_base=0.9) == pytest.approx(0.94)


def test_record_trade_updates_asset_b_accounting() -> None:
    cell = _cell()
    cell.record_trade(
        actor_type="noise",
        volume_b=1_000.0,
        lp_revenue_b=3.0,
        protocol_revenue_b=1.0,
        trader_cost_b=7.0,
        attributed_loss_b=5.0,
    )

    assert cell.epoch_volume_b == 1_000.0
    assert cell.epoch_lp_revenue_b == 3.0
    assert cell.epoch_protocol_revenue_b == 1.0
    assert cell.epoch_fees_total_b == 4.0
    assert cell.epoch_num_trades == 1
    assert cell.epoch_num_noise_trades == 1
