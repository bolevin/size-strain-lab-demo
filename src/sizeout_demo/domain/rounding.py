"""Rounding as values are published, so that densities match the paper's D and es.

Decimal and half up, applied to the value as it is written (twelve significant
digits), not to its binary form: 366.435 is 366.43499... in binary and would
otherwise round down.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sizeout_demo.domain.quantity import Quantity


@dataclass(frozen=True, slots=True)
class Rounded:
    quantity: Quantity
    decimals: int | None  # None: not rounded (no e.s.d. says how far)


def _decimal(value: float) -> Decimal:
    return Decimal(f"{value:.12g}")


def _quantize(x: Decimal, decimals: int) -> Decimal:
    return x.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def _significant(x: Decimal, digits: int) -> int:
    """The decimals that leave ``digits`` significant digits of x > 0.

    A carry costs a digit: 0.96 to one digit is 1, with no decimals - not 1.0.
    """
    decimals = digits - 1 - x.adjusted()
    if _quantize(x, decimals).adjusted() > x.adjusted():
        decimals -= 1
    return decimals


def _apply(x: Decimal, e: Decimal, decimals: int) -> Rounded:
    if _quantize(x, decimals) == 0:  # a value is never rounded away to zero
        decimals = _significant(x, 1)
    return Rounded(
        Quantity(float(_quantize(x, decimals)), float(_quantize(e, decimals))), decimals
    )


def _unrounded(q: Quantity) -> Rounded:
    return Rounded(q, None)


def round_size(q: Quantity) -> Rounded:
    """Whole numbers when dD >= 1 (366.43 +- 66.51 -> 366 +- 67); otherwise dD to one
    significant digit and D to the same decimal (366.43 +- 0.51 -> 366.4 +- 0.5)."""
    if not (q.value > 0.0 and math.isfinite(q.value)) or q.esd == 0.0:
        return _unrounded(q)
    x, e = _decimal(q.value), _decimal(q.esd)
    return _apply(x, e, 0 if e >= 1 else _significant(e, 1))


def round_strain(q: Quantity) -> Rounded:
    """The coarser of "two significant digits of es" and "two of des"
    (0.02653 +- 0.01154 -> 0.027 +- 0.012), but des never rounded away
    (0.02649 +- 0.0001154 -> 0.0265 +- 0.0001)."""
    if not q.value > 0.0:
        return _unrounded(q)
    x, e = _decimal(q.value), _decimal(q.esd)
    decimals = _significant(x, 2)
    if e > 0:
        decimals = min(decimals, _significant(e, 2))
        if _quantize(e, decimals) == 0:
            decimals = _significant(e, 1)
    return _apply(x, e, decimals)


def round_burgers(q: Quantity) -> Rounded:
    """db to one significant digit and b to the same decimal (0.3839943 +- 0.000106 ->
    0.3840 +- 0.0001)."""
    if not q.value > 0.0 or q.esd == 0.0:
        return _unrounded(q)
    x, e = _decimal(q.value), _decimal(q.esd)
    return _apply(x, e, _significant(e, 1))
