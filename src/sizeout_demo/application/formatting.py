"""How numbers are written for people - shared by the report and the window."""

from __future__ import annotations

import math

from sizeout_demo.domain import Quantity, round_burgers, round_size, round_strain

_SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
INFINITY = "∞"


def _fixed(value: float, decimals: int | None, fallback_sig: int = 4) -> str:
    if decimals is None:
        return f"{value:.{fallback_sig}g}"
    return f"{value:.{max(decimals, 0)}f}"


def size_text(q: Quantity) -> str:
    """D as published: "45 ± 2" (nm); the infinite crystallite as the sign."""
    if q.is_infinite:
        return INFINITY
    r = round_size(q)
    if r.decimals is None:
        return _fixed(q.value, None)
    return f"{_fixed(r.quantity.value, r.decimals)} ± {_fixed(r.quantity.esd, r.decimals)}"


def strain_text(q: Quantity) -> str:
    """es as published: "0.120 ± 0.008" (%)."""
    if not q.value > 0.0:
        return "0"
    r = round_strain(q)
    if q.esd == 0.0:
        return _fixed(r.quantity.value, r.decimals)
    return f"{_fixed(r.quantity.value, r.decimals)} ± {_fixed(r.quantity.esd, r.decimals)}"


def burgers_text(q: Quantity) -> str:
    r = round_burgers(q)
    if r.decimals is None:
        return f"{q.value:.6g}"
    return f"{_fixed(r.quantity.value, r.decimals)} ± {_fixed(r.quantity.esd, r.decimals)}"


def power_text(q: Quantity, digits: int = 3) -> str:
    """A density: "(5.21 ± 0.78)·10⁹" - both numbers on one power of ten."""
    if q.value == 0.0:
        return "0"
    exponent = math.floor(math.log10(abs(q.value)))
    scale = 10.0**exponent
    power = "10" + str(exponent).translate(_SUPERSCRIPT)
    mantissa = f"{q.value / scale:.{digits - 1}f}"
    if q.esd == 0.0:
        return f"{mantissa}·{power}"
    return f"({mantissa} ± {q.esd / scale:.{digits - 1}f})·{power}"


def number_text(value: float, sig: int = 6) -> str:
    """A plain number with ``sig`` significant digits, exponent where it helps."""
    if value == 0.0 or 1e-3 <= abs(value) < 1e6:
        return f"{value:.{sig}g}"
    return f"{value:.{sig - 1}e}"


def esd_text(q: Quantity, sig: int = 6) -> str:
    """A coefficient with its e.s.d., both in full: "4.1001e-03 ± 1.2e-04"."""
    return f"{number_text(q.value, sig)} ± {number_text(q.esd, 2)}"
