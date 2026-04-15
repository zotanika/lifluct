"""Thin wrapper for the Phase 2 multi-cell LIFLUCT configuration."""

from __future__ import annotations

from dataclasses import replace

from lifluct.core.simulation import SimulationRunner
from lifluct.types import RunConfig, SimulationResult


def run_lifluct_multi_cell(config: RunConfig) -> SimulationResult:
    runner = SimulationRunner(
        replace(
            config,
            baseline_type="lifluct_multi_cell",
            use_dynamic_fee=True,
            enable_evolution=True,
            num_cells=max(2, config.num_cells),
        )
    )
    return runner.run_single()
