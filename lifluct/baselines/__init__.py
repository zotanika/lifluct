"""Baseline wrappers for the Phase 1 simulator."""

from lifluct.baselines.dynamic_fee_single import run_dynamic_fee_single
from lifluct.baselines.static_cpmm import run_static_cpmm
from lifluct.baselines.lifluct_multi_cell import run_lifluct_multi_cell

__all__ = ["run_dynamic_fee_single", "run_static_cpmm", "run_lifluct_multi_cell"]
