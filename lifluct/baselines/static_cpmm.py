"""Static CPMM baseline wrapper."""

from __future__ import annotations

from dataclasses import replace

from lifluct.core.simulation import SimulationRunner
from lifluct.types import RunConfig, SimulationResult


def run_static_cpmm(config: RunConfig) -> SimulationResult:
    runner = SimulationRunner(
        replace(
            config,
            baseline_type="static_cpmm",
            use_dynamic_fee=False,
            use_turgor=False,
        )
    )
    return runner.run()
