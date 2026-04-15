"""Trade-generation helpers for the Phase 1 simulator."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from lifluct.constants import EPSILON
from lifluct.core.attribution import deviation
from lifluct.core.cluster import pool_price, tvl
from lifluct.types import ClusterState


@dataclass(slots=True)
class ProposedTrade:
    actor_type: str
    direction: str
    amount_in: float


def generate_noise_trade(
    rng: np.random.Generator,
    q_trade: float,
    state: ClusterState,
    oracle_price: float,
    max_trade_fraction_of_tvl: float,
) -> ProposedTrade | None:
    """Sample one Bernoulli-arrival noise trade."""
    if rng.random() >= q_trade:
        return None

    current_tvl = tvl(state, oracle_price)
    max_notional_b = max_trade_fraction_of_tvl * current_tvl
    notional_b = rng.uniform(0.0, max_notional_b)
    if notional_b <= EPSILON:
        return None

    direction = "a_to_b" if rng.random() < 0.5 else "b_to_a"
    amount_in = notional_b / oracle_price if direction == "a_to_b" else notional_b
    return ProposedTrade(actor_type="noise", direction=direction, amount_in=amount_in)


def build_arbitrage_trade(
    state: ClusterState,
    oracle_price: float,
    fee_rate: float,
    arbitrage_threshold: float,
) -> ProposedTrade | None:
    """
    Build a single arbitrage trade aimed at moving the pool toward the oracle.

    The reserve target is a simple approximation: it solves for the constant-product
    reserve pair whose price equals the external reference price, ignoring any
    secondary effects from fee retention. Phase 1 keeps this deliberately simple.
    """
    current_pool_price = pool_price(state)
    deviation_value = deviation(current_pool_price, oracle_price)
    if deviation_value <= arbitrage_threshold or fee_rate >= 1.0:
        return None

    invariant = state.reserve_a * state.reserve_b
    target_reserve_a = math.sqrt(invariant / oracle_price)
    target_reserve_b = math.sqrt(invariant * oracle_price)

    if current_pool_price > oracle_price:
        effective_amount_in_a = max(0.0, target_reserve_a - state.reserve_a)
        if effective_amount_in_a <= EPSILON:
            return None
        gross_amount_in_a = effective_amount_in_a / max(EPSILON, 1.0 - fee_rate)
        return ProposedTrade(
            actor_type="arbitrage",
            direction="a_to_b",
            amount_in=gross_amount_in_a,
        )

    effective_amount_in_b = max(0.0, target_reserve_b - state.reserve_b)
    if effective_amount_in_b <= EPSILON:
        return None
    gross_amount_in_b = effective_amount_in_b / max(EPSILON, 1.0 - fee_rate)
    return ProposedTrade(
        actor_type="arbitrage",
        direction="b_to_a",
        amount_in=gross_amount_in_b,
    )
