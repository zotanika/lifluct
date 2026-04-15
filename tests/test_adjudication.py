from lifluct.reporting.adjudication import adjudicate_family


def _paired_rows(
    *,
    lifluct_lp: float,
    dynamic_lp: float,
    best_fixed_lp: float,
    lifluct_cost: float = 0.0,
    dynamic_cost: float = 0.0,
    best_fixed_cost: float = 0.0,
    seeds: int = 8,
    family: str = "no_lysis",
) -> list[dict[str, float | int | str]]:
    lifluct_model = "lifluct_multi_cell_with_lysis" if family == "lysis_enabled" else "lifluct_multi_cell_no_lysis"
    dynamic_model = "dynamic_fee_single_with_lysis" if family == "lysis_enabled" else "dynamic_fee_single"
    best_fixed_model = "best_fixed_single_cell_with_lysis" if family == "lysis_enabled" else "best_fixed_single_cell"
    rows = []
    for seed in range(1, seeds + 1):
        for model_type, lp_value, trader_cost in [
            (lifluct_model, lifluct_lp, lifluct_cost),
            (dynamic_model, dynamic_lp, dynamic_cost),
            (best_fixed_model, best_fixed_lp, best_fixed_cost),
        ]:
            rows.append(
                {
                    "model_type": model_type,
                    "seed": seed,
                    "regime_id": "regime_demo",
                    "evaluation_split": "test",
                    "lp_minus_hodl_b": lp_value,
                    "total_trader_cost_b": trader_cost,
                }
            )
    return rows


def test_obvious_win_scenario_adjudicates_as_survives() -> None:
    result = adjudicate_family(
        _paired_rows(lifluct_lp=2.0, dynamic_lp=1.0, best_fixed_lp=2.0),
        [],
        family_name="family_demo",
        model_family="no_lysis",
    )

    assert result.verdict == "survives"


def test_obvious_failure_scenario_adjudicates_as_fails() -> None:
    prevalence_rows = [
        {
            "model_type": "lifluct_multi_cell_no_lysis",
            "failure_flag": "lysis_cascade",
            "severity": "critical",
            "fraction_of_runs": 0.6,
            "avg_failure_flags_per_run": 0.6,
            "critical_fraction": 0.6,
        }
    ]
    result = adjudicate_family(
        _paired_rows(lifluct_lp=-2.0, dynamic_lp=1.0, best_fixed_lp=1.5),
        prevalence_rows,
        family_name="family_demo",
        model_family="no_lysis",
    )

    assert result.verdict == "fails"


def test_low_sample_scenario_is_inconclusive() -> None:
    result = adjudicate_family(
        _paired_rows(lifluct_lp=2.0, dynamic_lp=1.0, best_fixed_lp=1.5, seeds=2),
        [],
        family_name="family_demo",
        model_family="no_lysis",
    )

    assert result.verdict == "inconclusive"
