import numpy as np

from lifluct.core.cell import CellGenes, CellState
from lifluct.core.routing import choose_user_cell


def _cells() -> list[CellState]:
    return [
        CellState(
            cell_id=0,
            active=True,
            lysis_triggered=False,
            generation_index=0,
            parent_cell_id=None,
            genes=CellGenes(0.003, 0.1, 0.002, 0.1),
            weight_user_routing=1.0,
        ),
        CellState(
            cell_id=1,
            active=False,
            lysis_triggered=False,
            generation_index=0,
            parent_cell_id=None,
            genes=CellGenes(0.002, 0.1, 0.002, 0.1),
            weight_user_routing=100.0,
        ),
        CellState(
            cell_id=2,
            active=True,
            lysis_triggered=False,
            generation_index=0,
            parent_cell_id=None,
            genes=CellGenes(0.004, 0.1, 0.002, 0.1),
            weight_user_routing=2.0,
        ),
    ]


def test_weighted_random_only_chooses_active_cells() -> None:
    rng = np.random.default_rng(3)
    cells = _cells()
    fee_map = {0: 0.003, 2: 0.004}

    chosen_ids = {
        choose_user_cell(cells, "weighted_random", fee_map, rng).cell_id
        for _ in range(100)
    }

    assert chosen_ids <= {0, 2}
    assert 1 not in chosen_ids


def test_cheapest_fee_picks_minimum_fee_active_cell() -> None:
    rng = np.random.default_rng(3)
    cells = _cells()
    fee_map = {0: 0.003, 2: 0.001}

    chosen = choose_user_cell(cells, "cheapest_fee", fee_map, rng)

    assert chosen is not None
    assert chosen.cell_id == 2
