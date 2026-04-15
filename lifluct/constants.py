"""Shared constants for the Phase 1 simulator."""

from __future__ import annotations

EPSILON = 1e-12
DEFAULT_DT = 1.0
DEFAULT_ORACLE_OBSERVATION_NOISE = 0.01
DEFAULT_OUTPUT_DIR = "runs"
DEFAULT_PLOTS_DIRNAME = "plots"

SUPPORTED_BASELINES = {
    "static_cpmm",
    "dynamic_fee_single",
    "lifluct_multi_cell",
    "best_fixed_single_cell",
}

SUPPORTED_ORACLE_MODES = {
    "perfect",
    "lagged",
    "noisy",
}

PLOT_FILE_NAMES = {
    "lp_vs_hodl": "lp_vs_hodl.png",
    "cumulative_fees": "cumulative_fees.png",
    "cumulative_attributed_loss": "cumulative_attributed_loss.png",
    "cumulative_trader_cost": "cumulative_trader_cost.png",
    "oracle_vs_pool_price": "oracle_vs_pool_price.png",
    "epoch_attributed_loss": "epoch_attributed_loss.png",
    "epoch_lp_revenue": "epoch_lp_revenue.png",
    "active_cells": "active_cells.png",
    "lysis_events": "lysis_events.png",
    "f_min_trajectories": "f_min_trajectories.png",
    "mu_trajectories": "mu_trajectories.png",
    "tau_trajectories": "tau_trajectories.png",
    "beta_trajectories": "beta_trajectories.png",
    "revenue_vs_loss_scatter": "revenue_vs_loss_scatter.png",
    "surviving_gene_histogram": "surviving_gene_histogram.png",
    "gene_variance_by_epoch": "gene_variance_by_epoch.png",
    "all_cells_inactive_over_time": "all_cells_inactive_over_time.png",
    "lysis_cascade_timeline": "lysis_cascade_timeline.png",
    "lp_minus_hodl_vs_omega": "lp_minus_hodl_vs_omega.png",
    "lp_minus_hodl_vs_sigma": "lp_minus_hodl_vs_sigma.png",
    "lp_minus_hodl_vs_oracle_lag": "lp_minus_hodl_vs_oracle_lag.png",
    "lp_outcome_heatmap_omega_sigma": "lp_outcome_heatmap_omega_sigma.png",
    "lp_outcome_heatmap_oracle_lag_kappa": "lp_outcome_heatmap_oracle_lag_kappa.png",
    "seed_variance_lp_minus_hodl": "seed_variance_lp_minus_hodl.png",
    "lp_vs_trader_frontier": "lp_vs_trader_frontier.png",
    "lp_vs_trader_frontier_vs_best_fixed": "lp_vs_trader_frontier_vs_best_fixed.png",
    "attributed_loss_vs_oracle_lag": "attributed_loss_vs_oracle_lag.png",
    "lysis_count_vs_oracle_lag": "lysis_count_vs_oracle_lag.png",
    "top_cell_concentration": "top_cell_concentration.png",
    "attribution_mode_ranking_stability": "attribution_mode_ranking_stability.png",
    "best_fixed_vs_turgor": "best_fixed_vs_turgor.png",
    "failure_regime_timeline": "failure_regime_timeline.png",
}
