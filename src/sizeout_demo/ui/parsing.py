"""From the text in the fields to domain values, with messages that name the field."""

from __future__ import annotations

import math

from sizeout_demo.domain import (
    CubicBurgers,
    DislocationSettings,
    EnteredBurgers,
    Instrument,
    Quantity,
    ReferenceModels,
)
from sizeout_demo.ui.view import (
    DislocationInput,
    InstrumentInput,
    PairInput,
    ReferenceInput,
)


class InputError(ValueError):
    """A field holds something that is not the number it should be."""


def number(text: str, name: str) -> float | None:
    """The number in ``text`` (a decimal comma is accepted); None if the field is empty."""
    cleaned = text.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        raise InputError(f"{name}: {text.strip()!r} is not a number") from None
    if not math.isfinite(value):
        raise InputError(f"{name} must be a finite number")
    return value


def required(text: str, name: str) -> float:
    value = number(text, name)
    if value is None:
        raise InputError(f"{name} is empty")
    return value


def integer(text: str, name: str) -> int:
    value = required(text, name)
    if value != int(value):
        raise InputError(f"{name} must be a whole number")
    return int(value)


def pair(p: PairInput, name: str) -> Quantity | None:
    """A value with its e.s.d.; None when the value is empty, an empty e.s.d. is 0."""
    value = number(p.value, name)
    if value is None:
        return None
    esd = number(p.esd, f"the e.s.d. of {name}") or 0.0
    if esd < 0.0:
        raise InputError(f"the e.s.d. of {name} must not be negative")
    return Quantity(value, esd)


def required_pair(p: PairInput, name: str) -> Quantity:
    q = pair(p, name)
    if q is None:
        raise InputError(f"{name} is empty")
    return q


def positive_pair(p: PairInput, name: str) -> Quantity | None:
    """A value that has to be > 0 when it is set; empty or <= 0 means "not set"."""
    q = pair(p, name)
    return q if q is not None and q.value > 0.0 else None


def instrument(i: InstrumentInput) -> Instrument:
    return Instrument(
        required(i.wavelength, "Wavelength"),
        required(i.k_size, "K_size"),
        required(i.k_strain, "K_strain"),
    )


def references(r: ReferenceInput) -> ReferenceModels:
    return ReferenceModels(
        scherrer=positive_pair(r.scherrer, "D0 (Scherrer)"),
        monshi=positive_pair(r.monshi, "D0 (Monshi)"),
        stokes=positive_pair(r.stokes, "es_inf (Stokes)"),
    )


def dislocations(d: DislocationInput, *, force: bool = False) -> DislocationSettings | None:
    """The dislocation parameters, or None when the switch is off (``force`` ignores it)."""
    if not (d.enabled or force):
        return None
    if d.cubic:
        burgers: CubicBurgers | EnteredBurgers = CubicBurgers(
            required_pair(d.a, "a"),
            integer(d.m, "m"),
            (integer(d.uvw[0], "u"), integer(d.uvw[1], "v"), integer(d.uvw[2], "w")),
        )
    else:
        burgers = EnteredBurgers(required_pair(d.b, "b"))
    return DislocationSettings(
        n=required(d.n, "n"),
        distribution=d.distribution,
        k=required(d.k, "k"),
        burgers=burgers,
        round_inputs=d.rounded,
    )
