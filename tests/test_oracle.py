from lifluct.core.oracle import OracleProcess
from lifluct.types import RunConfig


def _base_config(**updates: object) -> RunConfig:
    raw = {
        "seed": 7,
        "num_steps": 10,
        "initial_reserve_a": 1_000.0,
        "initial_reserve_b": 100_000.0,
        "initial_price": 100.0,
        "sigma": 0.02,
        "q_trade": 0.25,
        "max_trade_fraction_of_tvl": 0.02,
        "arbitrage_threshold": 0.001,
        "baseline_type": "static_cpmm",
        "f_min": 0.003,
        "mu": 0.15,
        "tau": 0.002,
        "s_base": 1.0,
        "beta": 0.0,
        "tvl_target": 200_000.0,
        "oracle_mode": "perfect",
        "oracle_lag_steps": 0,
        "use_dynamic_fee": False,
        "use_turgor": False,
        "dt": 1.0,
        "oracle_observation_noise": 0.01,
    }
    raw.update(updates)
    return RunConfig.from_mapping(raw)


def test_oracle_process_is_deterministic_from_seed() -> None:
    config = _base_config()
    oracle_one = OracleProcess(config)
    oracle_two = OracleProcess(config)

    path_one = [oracle_one.current()]
    path_two = [oracle_two.current()]
    for _ in range(5):
        path_one.append(oracle_one.step())
        path_two.append(oracle_two.step())

    assert [(state.true_price, state.observed_price) for state in path_one] == [
        (state.true_price, state.observed_price) for state in path_two
    ]


def test_lagged_observed_price_uses_history() -> None:
    config = _base_config(oracle_mode="lagged", oracle_lag_steps=2)
    oracle = OracleProcess(config)

    state_1 = oracle.step()
    state_2 = oracle.step()
    state_3 = oracle.step()

    assert state_1.observed_price == config.initial_price
    assert state_2.observed_price == config.initial_price
    assert state_3.observed_price == oracle.true_price_history[1]
