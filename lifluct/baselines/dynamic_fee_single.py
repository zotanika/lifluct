"""Single dynamic-fee baseline wrapper."""

from __future__ import annotations

from dataclasses import replace

from lifluct.core.simulation import SimulationRunner
from lifluct.types import RunConfig, SimulationResult


def run_dynamic_fee_single(
    config: RunConfig,
    *,
    use_turgor: bool | None = None,
) -> SimulationResult:
    runner = SimulationRunner(
        replace(
            config,
            baseline_type="dynamic_fee_single",
            use_dynamic_fee=True,
            use_turgor=config.use_turgor if use_turgor is None else use_turgor,
        )
    )
    return runner.run()
