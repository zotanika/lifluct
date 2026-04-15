from lifluct.core.cell import CellGenes, CellState
from lifluct.core.lysis import apply_lysis, should_lyse


def _cell() -> CellState:
    cell = CellState(
        cell_id=0,
        active=True,
        lysis_triggered=False,
        generation_index=0,
        parent_cell_id=None,
        genes=CellGenes(0.003, 0.1, 0.002, 0.1),
    )
    cell.epoch_fees_total_b = 10.0
    cell.epoch_attributed_loss_b = 40.0
    return cell


def test_lysis_triggers_when_loss_exceeds_kappa_times_fees() -> None:
    assert should_lyse(_cell(), kappa=3.0) is True


def test_hard_lysis_deactivates_cell() -> None:
    cell = _cell()
    apply_lysis(cell, lysis_mode="hard", soft_penalty=0.05)

    assert cell.lysis_triggered is True
    assert cell.active is False
