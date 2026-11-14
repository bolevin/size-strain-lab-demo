"""The straight line y = A + B*x: least squares through many points, or through two."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from sizeout_demo.domain.errors import InsufficientData, InvalidInput
from sizeout_demo.domain.quantity import Quantity

#: Two points give a line but no scatter to estimate its e.s.d.'s from.
MIN_FIT_POINTS = 3


@dataclass(frozen=True, slots=True)
class Line:
    intercept: Quantity  # A
    slope: Quantity  # B
    r_squared: float | None = None  # coefficient of determination; None if not fitted
    n_points: int = 0

    def at(self, x: float) -> float:
        return self.intercept.value + self.slope.value * x


@dataclass(frozen=True, slots=True)
class Point:
    """A point of the plot with the e.s.d.'s of both coordinates."""

    x: Quantity
    y: Quantity


def fit_line(xs: Sequence[float], ys: Sequence[float]) -> Line:
    """Ordinary least squares with the usual standard errors.

    dB = sqrt(s2 / Sxx), dA = sqrt(s2 * (1/n + xbar^2 / Sxx)), s2 = SSres / (n - 2).
    """
    n = len(xs)
    if n != len(ys):
        raise InvalidInput("x and y must have the same length")
    if n < MIN_FIT_POINTS:
        raise InsufficientData(
            f"{n} reflection(s): a fit needs at least {MIN_FIT_POINTS} - "
            "two give a line, but no e.s.d.'s"
        )
    x_mean, y_mean = math.fsum(xs) / n, math.fsum(ys) / n
    sxx = math.fsum((x - x_mean) ** 2 for x in xs)
    if sxx <= 0.0:
        raise InvalidInput("all points have the same x: the slope is undefined")
    sxy = math.fsum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True))
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    ss_res = math.fsum(
        (y - intercept - slope * x) ** 2 for x, y in zip(xs, ys, strict=True)
    )
    ss_tot = math.fsum((y - y_mean) ** 2 for y in ys)
    s2 = ss_res / (n - 2)
    return Line(
        intercept=Quantity(intercept, math.sqrt(s2 * (1.0 / n + x_mean**2 / sxx))),
        slope=Quantity(slope, math.sqrt(s2 / sxx)),
        r_squared=1.0 - ss_res / ss_tot if ss_tot > 0.0 else 1.0,
        n_points=n,
    )


def line_through(first: Point, second: Point) -> Line:
    """The line through two points, the e.s.d.'s propagated from theirs.

    B = (y2 - y1) / (x2 - x1),   dB = |B| * sqrt((s_dx / dx)^2 + (s_dy / dy)^2),
    A = y1 - B * x1,             dA = sqrt(s_y1^2 + (B x1)^2 ((dB / B)^2 + (s_x1 / x1)^2)).

    The last term is written as (x1 * dB)^2 + (B * s_x1)^2, the same number without
    a division by B or x1; a horizontal line (dy = 0) takes the limit s_dy / |dx|.
    """
    dx = second.x.value - first.x.value
    dy = second.y.value - first.y.value
    if dx == 0.0:
        raise InvalidInput("the two points have the same x: the slope is undefined")
    slope = dy / dx
    s_dx = math.hypot(first.x.esd, second.x.esd)
    s_dy = math.hypot(first.y.esd, second.y.esd)
    d_slope = abs(slope) * math.hypot(s_dx / dx, s_dy / dy) if dy != 0.0 else s_dy / abs(dx)
    x1 = first.x.value
    return Line(
        intercept=Quantity(
            first.y.value - slope * x1,
            math.hypot(first.y.esd, x1 * d_slope, slope * first.x.esd),
        ),
        slope=Quantity(slope, d_slope),
        r_squared=None,
        n_points=2,
    )
