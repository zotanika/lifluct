"""Constant-product pool math for the Phase 1 simulator."""

from __future__ import annotations

from dataclasses import dataclass

from lifluct.constants import EPSILON
from lifluct.types import ClusterState


@dataclass(slots=True)
class SwapExecution:
    amount_in: float
    amount_out: float
    exec_price: float
    fee_rate: float
    total_fee_amount_in: float
    lp_fee_amount_in: float
    protocol_fee_amount_in: float
    effective_amount_in: float
    pool_price_before: float
    pool_price_after: float


def pool_price(state: ClusterState) -> float:
    """Return the pool price in asset-B per asset-A."""
    if state.reserve_a <= EPSILON:
        raise ValueError("reserve_a must remain positive")
    return state.reserve_b / state.reserve_a


def tvl(state: ClusterState, oracle_price: float) -> float:
    """Return total value locked in asset-B numeraire."""
    return state.reserve_a * oracle_price + state.reserve_b


def swap_a_to_b(
    state: ClusterState,
    amount_in_a: float,
    fee_rate: float,
    lp_share_value: float = 1.0,
) -> tuple[ClusterState, SwapExecution]:
    """Swap asset A into the pool and receive asset B."""
    if amount_in_a <= 0:
        raise ValueError("amount_in_a must be positive")
    if not 0 <= fee_rate < 1:
        raise ValueError("fee_rate must satisfy 0 <= fee_rate < 1")

    price_before = pool_price(state)
    total_fee_a = amount_in_a * fee_rate
    lp_fee_a = total_fee_a * lp_share_value
    protocol_fee_a = total_fee_a - lp_fee_a
    effective_amount_in_a = amount_in_a - total_fee_a

    invariant = state.reserve_a * state.reserve_b
    effective_reserve_a = state.reserve_a + effective_amount_in_a
    new_reserve_b = invariant / effective_reserve_a
    amount_out_b = state.reserve_b - new_reserve_b
    new_reserve_a = state.reserve_a + amount_in_a - protocol_fee_a

    new_state = ClusterState(reserve_a=new_reserve_a, reserve_b=new_reserve_b)
    execution = SwapExecution(
        amount_in=amount_in_a,
        amount_out=amount_out_b,
        exec_price=amount_out_b / amount_in_a,
        fee_rate=fee_rate,
        total_fee_amount_in=total_fee_a,
        lp_fee_amount_in=lp_fee_a,
        protocol_fee_amount_in=protocol_fee_a,
        effective_amount_in=effective_amount_in_a,
        pool_price_before=price_before,
        pool_price_after=pool_price(new_state),
    )
    return new_state, execution


def swap_b_to_a(
    state: ClusterState,
    amount_in_b: float,
    fee_rate: float,
    lp_share_value: float = 1.0,
) -> tuple[ClusterState, SwapExecution]:
    """Swap asset B into the pool and receive asset A."""
    if amount_in_b <= 0:
        raise ValueError("amount_in_b must be positive")
    if not 0 <= fee_rate < 1:
        raise ValueError("fee_rate must satisfy 0 <= fee_rate < 1")

    price_before = pool_price(state)
    total_fee_b = amount_in_b * fee_rate
    lp_fee_b = total_fee_b * lp_share_value
    protocol_fee_b = total_fee_b - lp_fee_b
    effective_amount_in_b = amount_in_b - total_fee_b

    invariant = state.reserve_a * state.reserve_b
    effective_reserve_b = state.reserve_b + effective_amount_in_b
    new_reserve_a = invariant / effective_reserve_b
    amount_out_a = state.reserve_a - new_reserve_a
    new_reserve_b = state.reserve_b + amount_in_b - protocol_fee_b

    new_state = ClusterState(reserve_a=new_reserve_a, reserve_b=new_reserve_b)
    execution = SwapExecution(
        amount_in=amount_in_b,
        amount_out=amount_out_a,
        exec_price=amount_in_b / amount_out_a,
        fee_rate=fee_rate,
        total_fee_amount_in=total_fee_b,
        lp_fee_amount_in=lp_fee_b,
        protocol_fee_amount_in=protocol_fee_b,
        effective_amount_in=effective_amount_in_b,
        pool_price_before=price_before,
        pool_price_after=pool_price(new_state),
    )
    return new_state, execution
