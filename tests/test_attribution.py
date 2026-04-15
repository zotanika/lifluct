import pytest

from lifluct.core.attribution import attributed_loss_b, deviation, dynamic_fee


def test_deviation_calculation() -> None:
    assert deviation(pool_price=102.0, oracle_price=100.0) == pytest.approx(0.02)


def test_dynamic_fee_calculation() -> None:
    result = dynamic_fee(f_min=0.003, mu=0.15, tau=0.002, deviation_value=0.01)
    assert result == 0.003 + 0.15 * 0.008


def test_attributed_loss_zero_when_deviation_is_inside_fee_band() -> None:
    loss = attributed_loss_b(
        exec_price=100.2,
        oracle_price=100.0,
        volume_b=1_000.0,
        fee_rate=0.003,
    )
    assert loss == 0.0


def test_attributed_loss_positive_when_deviation_exceeds_fee_band() -> None:
    loss = attributed_loss_b(
        exec_price=101.0,
        oracle_price=100.0,
        volume_b=1_000.0,
        fee_rate=0.003,
    )
    assert loss > 0.0
