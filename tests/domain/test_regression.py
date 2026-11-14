"""The straight line, checked against sums done by hand."""

from __future__ import annotations

import math

import pytest

from sizeout_demo.domain import (
    InsufficientData,
    InvalidInput,
    Point,
    Quantity,
    fit_line,
    line_through,
)


def test_least_squares_on_four_points_by_hand() -> None:
    # x = 0..3, y = 1, 3, 4, 7: xbar 1.5, ybar 3.75, Sxx 5, Sxy 9.5, SSres 0.70, SStot 18.75
    line = fit_line([0.0, 1.0, 2.0, 3.0], [1.0, 3.0, 4.0, 7.0])
    assert line.slope.value == pytest.approx(1.9)
    assert line.intercept.value == pytest.approx(0.9)
    assert line.slope.esd == pytest.approx(math.sqrt(0.35 / 5))  # 0.264575
    assert line.intercept.esd == pytest.approx(math.sqrt(0.35 * 0.7))  # 0.494975
    assert line.r_squared == pytest.approx(1 - 0.70 / 18.75)
    assert line.n_points == 4


def test_points_on_a_line_give_it_exactly_and_no_scatter() -> None:
    line = fit_line([1.0, 2.0, 5.0], [3.5, 5.0, 9.5])
    assert (line.intercept.value, line.slope.value) == pytest.approx((2.0, 1.5))
    assert line.slope.esd == pytest.approx(0.0, abs=1e-15)
    assert line.r_squared == pytest.approx(1.0)


def test_two_points_are_not_a_fit() -> None:
    with pytest.raises(InsufficientData, match="at least 3"):
        fit_line([1.0, 2.0], [1.0, 2.0])


def test_equal_x_has_no_slope() -> None:
    with pytest.raises(InvalidInput, match="same x"):
        fit_line([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])


def test_line_through_two_points_propagates_their_esds() -> None:
    # (1 +- 0.1, 2 +- 0.2) and (3 +- 0.1, 6 +- 0.2): B = 2, dB = 2 * sqrt(2 * 0.005) = 0.2
    line = line_through(
        Point(Quantity(1.0, 0.1), Quantity(2.0, 0.2)),
        Point(Quantity(3.0, 0.1), Quantity(6.0, 0.2)),
    )
    assert line.slope.value == pytest.approx(2.0)
    assert line.slope.esd == pytest.approx(0.2)
    assert line.intercept.value == pytest.approx(0.0)
    # sqrt(0.2^2 + (1 * 0.2)^2 + (2 * 0.1)^2)
    assert line.intercept.esd == pytest.approx(math.sqrt(0.12))
    assert line.r_squared is None


def test_line_through_two_points_matches_the_authors_form() -> None:
    """dA = sqrt(s_y1^2 + (B x1)^2 ((dB/B)^2 + (s_x1/x1)^2)), written without division."""
    p1, p2 = (
        Point(Quantity(0.4, 0.03), Quantity(1.1, 0.05)),
        Point(Quantity(2.5, 0.02), Quantity(3.9, 0.07)),
    )
    line = line_through(p1, p2)
    b, db, x1 = line.slope.value, line.slope.esd, p1.x.value
    authors = math.sqrt(
        p1.y.esd**2 + (b * x1) ** 2 * ((db / b) ** 2 + (p1.x.esd / x1) ** 2)
    )
    assert line.intercept.esd == pytest.approx(authors)


def test_a_horizontal_line_through_two_points_has_a_finite_slope_esd() -> None:
    line = line_through(
        Point(Quantity(1.0), Quantity(2.0, 0.3)), Point(Quantity(3.0), Quantity(2.0, 0.4))
    )
    assert line.slope.value == 0.0
    assert line.slope.esd == pytest.approx(0.5 / 2.0)
