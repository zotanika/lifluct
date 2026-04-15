"""Oracle price process helpers for the Phase 1 simulator."""

from __future__ import annotations

import math

import numpy as np

from lifluct.types import OracleState, RunConfig


def geometric_brownian_motion_step(
    price: float,
    sigma: float,
    rng: np.random.Generator,
    dt: float,
) -> float:
    """Advance a zero-drift GBM process by one discrete step."""
    shock = rng.normal(loc=0.0, scale=sigma * math.sqrt(dt))
    return price * math.exp(shock)


class OracleProcess:
    """Deterministic oracle state machine with observed-price wrappers."""

    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.step_index = 0
        self.true_price_history: list[float] = [config.initial_price]
        self.current_state = OracleState(
            true_price=config.initial_price,
            observed_price=config.initial_price,
            step=0,
        )

    def current(self) -> OracleState:
        return self.current_state

    def step(self) -> OracleState:
        self.step_index += 1
        next_true_price = geometric_brownian_motion_step(
            price=self.current_state.true_price,
            sigma=self.config.sigma,
            rng=self.rng,
            dt=self.config.dt,
        )
        self.true_price_history.append(next_true_price)
        observed_price = self._observed_price(next_true_price)
        self.current_state = OracleState(
            true_price=next_true_price,
            observed_price=observed_price,
            step=self.step_index,
        )
        return self.current_state

    def _observed_price(self, true_price: float) -> float:
        if self.config.oracle_mode == "perfect":
            return true_price
        if self.config.oracle_mode == "lagged":
            history_index = max(0, self.step_index - self.config.oracle_lag_steps)
            return self.true_price_history[history_index]
        if self.config.oracle_mode == "noisy":
            noise = self.rng.normal(loc=0.0, scale=self.config.oracle_observation_noise)
            return true_price * math.exp(noise)
        raise ValueError(f"unsupported oracle mode: {self.config.oracle_mode}")
