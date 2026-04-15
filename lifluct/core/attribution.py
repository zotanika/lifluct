"""Deviation, fee, and attribution helpers for the Phase 1 simulator."""

from __future__ import annotations


def deviation(pool_price: float, oracle_price: float) -> float:
    return abs(pool_price / oracle_price - 1.0)


def dynamic_fee(f_min: float, mu: float, tau: float, deviation_value: float) -> float:
    return f_min + mu * max(0.0, deviation_value - tau)


def lifluct_pressure(tvl: float, tvl_target: float) -> float:
    if tvl_target <= 0:
        raise ValueError("tvl_target must be positive")
    return max(0.0, (tvl_target - tvl) / tvl_target)


def lp_share(s_base: float, beta: float, pressure: float) -> float:
    return min(1.0, max(0.0, s_base + beta * pressure))


def attributed_loss_b(
    exec_price: float,
    oracle_price: float,
    volume_b: float,
    fee_rate: float,
) -> float:
    return volume_b * max(0.0, abs(exec_price / oracle_price - 1.0) - fee_rate)


def trader_cost_proxy_b(
    exec_price: float,
    oracle_price: float,
    volume_b: float,
    fee_rate: float,
    fee_amount_b: float | None = None,
) -> float:
    """
    Heuristic trader-cost proxy.

    This intentionally is not an exact welfare measure. It combines:
    - fee paid in asset-B numeraire, and
    - excess execution-vs-oracle deviation beyond the explicit fee rate

    The second term is a rough slippage proxy only.
    """
    fee_component_b = fee_amount_b if fee_amount_b is not None else volume_b * fee_rate
    slippage_proxy_b = volume_b * max(0.0, abs(exec_price / oracle_price - 1.0) - fee_rate)
    return fee_component_b + slippage_proxy_b
