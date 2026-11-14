"""Rounding as published - the author's own examples."""

from __future__ import annotations

import pytest

from sizeout_demo.domain import Quantity, round_burgers, round_size, round_strain


@pytest.mark.parametrize(
    ("value", "esd", "expected", "decimals"),
    [
        (366.43, 66.51, (366.0, 67.0), 0),  # dD >= 1: whole numbers
        (366.43, 0.51, (366.4, 0.5), 1),  # dD < 1: one digit of dD
        (366.435, 0.51, (366.4, 0.5), 1),
        (0.9612, 0.0461, (0.96, 0.05), 2),
        (12.3456, 0.0234, (12.35, 0.02), 2),
    ],
)
def test_size(
    value: float, esd: float, expected: tuple[float, float], decimals: int
) -> None:
    r = round_size(Quantity(value, esd))
    assert (r.quantity.value, r.quantity.esd) == pytest.approx(expected)
    assert r.decimals == decimals


@pytest.mark.parametrize(
    ("value", "esd", "expected"),
    [
        (0.02653, 0.01154, (0.027, 0.012)),  # two digits of each, the coarser
        (0.02649, 0.201154, (0.03, 0.20)),
        (0.02649, 0.0001154, (0.0265, 0.0001)),  # des is never rounded away
        (1.2345, 0.0, (1.2, 0.0)),  # no e.s.d.: two digits of es
    ],
)
def test_strain(value: float, esd: float, expected: tuple[float, float]) -> None:
    r = round_strain(Quantity(value, esd))
    assert (r.quantity.value, r.quantity.esd) == pytest.approx(expected)


def test_burgers_vector() -> None:
    r = round_burgers(Quantity(0.3839943, 1.06066e-4))
    assert (r.quantity.value, r.quantity.esd, r.decimals) == pytest.approx(
        (0.3840, 0.0001, 4)
    )


def test_half_up_on_the_written_value_not_the_binary_one() -> None:
    # 2.675 is 2.67499999... in binary; written, it is 2.675 and rounds up
    r = round_size(Quantity(2.675, 0.01))
    assert r.quantity.value == pytest.approx(2.68)


def test_a_carry_costs_a_digit() -> None:
    r = round_size(Quantity(10.0, 0.96))
    assert (r.quantity.value, r.quantity.esd, r.decimals) == (10.0, 1.0, 0)


def test_nothing_to_go_by_leaves_the_value_alone() -> None:
    for rounded in (round_size(Quantity(43.28)), round_burgers(Quantity(0.2863))):
        assert rounded.decimals is None
    assert round_size(Quantity(float("inf"))).decimals is None
    assert round_strain(Quantity(0.0)).decimals is None
