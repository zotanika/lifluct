from lifluct.core.cluster import pool_price, swap_a_to_b, swap_b_to_a
from lifluct.types import ClusterState


def test_swap_a_to_b_moves_price_down_and_keeps_reserves_positive() -> None:
    state = ClusterState(reserve_a=1_000.0, reserve_b=100_000.0)

    new_state, execution = swap_a_to_b(state, amount_in_a=10.0, fee_rate=0.003)

    assert execution.amount_out > 0.0
    assert new_state.reserve_a > 0.0
    assert new_state.reserve_b > 0.0
    assert execution.pool_price_after < execution.pool_price_before
    assert pool_price(new_state) < pool_price(state)


def test_swap_b_to_a_moves_price_up_and_keeps_reserves_positive() -> None:
    state = ClusterState(reserve_a=1_000.0, reserve_b=100_000.0)

    new_state, execution = swap_b_to_a(state, amount_in_b=1_000.0, fee_rate=0.003)

    assert execution.amount_out > 0.0
    assert new_state.reserve_a > 0.0
    assert new_state.reserve_b > 0.0
    assert execution.pool_price_after > execution.pool_price_before
    assert pool_price(new_state) > pool_price(state)


def test_fee_retention_increases_effective_invariant() -> None:
    state = ClusterState(reserve_a=1_000.0, reserve_b=100_000.0)
    invariant_before = state.reserve_a * state.reserve_b

    new_state, _ = swap_a_to_b(state, amount_in_a=10.0, fee_rate=0.003, lp_share_value=1.0)
    invariant_after = new_state.reserve_a * new_state.reserve_b

    assert invariant_after > invariant_before
