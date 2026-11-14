"""The calculator: the broadening one reflection gets from D and es, and back.

    FWHM_size   = K_size * lambda / (D cos theta)          (radians, then degrees)
    FWHM_strain = K_strain * es/100 * tan theta
    dFWHM_size   = FWHM_size   * sqrt((dD/D)^2 + (dtheta tan theta)^2)
    dFWHM_strain = FWHM_strain * sqrt((des/es)^2 + (dtheta / (cos theta sin theta))^2)

The total width without the instrument follows the profile: the sum (Lorentz), the
root of the sum of squares (Gauss), or (s + sqrt(s^2 + 4 t^2)) / 2, the root of
beta = s + t^2 / beta (pseudo-Voigt).

Three ways in, one at a time: D and / or es; the two widths; the two dislocation
densities (then D for es = 0 and es for D = infinity, each on its own, no total).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from sizeout_demo.domain.dislocations import DislocationSettings
from sizeout_demo.domain.errors import InvalidInput
from sizeout_demo.domain.instrument import Instrument, Profile
from sizeout_demo.domain.quantity import INFINITE, ZERO, Quantity
from sizeout_demo.domain.rounding import round_burgers, round_size, round_strain


class Origin(Enum):
    MICROSTRUCTURE = "D and es"
    WIDTHS = "FWHM_size and FWHM_strain"
    DENSITIES = "Ldis_D and Ldis_es"


@dataclass(frozen=True, slots=True)
class Broadening:
    """Widths in degrees; None where not calculated."""

    size: Quantity | None
    strain: Quantity | None
    total: Quantity | None


@dataclass(frozen=True, slots=True)
class Estimate:
    origin: Origin
    two_theta: Quantity
    size: Quantity | None  # nm, infinite = no size broadening; None = not estimated
    strain: Quantity | None  # %
    broadening: Broadening
    burgers: Quantity | None = None  # as used, when estimated from the densities
    rounded: bool = False


def _check_angle(two_theta: Quantity) -> None:
    if not 0.0 < two_theta.value < 180.0:
        raise InvalidInput("2Theta of the reflection must lie between 0 and 180 deg")


def size_width(size: Quantity, two_theta: Quantity, instrument: Instrument) -> Quantity:
    if size.is_infinite:
        return ZERO
    th, dth = math.radians(two_theta.value / 2.0), math.radians(two_theta.esd / 2.0)
    width = math.degrees(
        instrument.k_size * instrument.wavelength_nm / (size.value * math.cos(th))
    )
    return Quantity(width, width * math.hypot(size.esd / size.value, dth * math.tan(th)))


def strain_width(strain: Quantity, two_theta: Quantity, instrument: Instrument) -> Quantity:
    if not strain.is_positive:
        return ZERO
    th, dth = math.radians(two_theta.value / 2.0), math.radians(two_theta.esd / 2.0)
    width = math.degrees(instrument.k_strain * strain.value / 100.0 * math.tan(th))
    return Quantity(
        width,
        width * math.hypot(strain.esd / strain.value, dth / (math.cos(th) * math.sin(th))),
    )


def total_width(profile: Profile, size: Quantity, strain: Quantity) -> Quantity:
    s, t = size.value, strain.value
    if profile is Profile.LORENTZ:
        return Quantity(s + t, math.hypot(size.esd, strain.esd))
    if profile is Profile.GAUSS:
        total = math.hypot(s, t)
        esd = math.hypot(s * size.esd, t * strain.esd) / total if total else 0.0
        return Quantity(total, esd)
    root = math.sqrt(s * s + 4.0 * t * t)
    if root == 0.0:
        return ZERO
    return Quantity(
        (s + root) / 2.0,
        0.5 * math.hypot(size.esd * (1.0 + s / root), 4.0 * t * strain.esd / root),
    )


def from_microstructure(
    size: Quantity | None,
    strain: Quantity | None,
    two_theta: Quantity,
    instrument: Instrument,
    profile: Profile,
    *,
    round_inputs: bool = False,
) -> Estimate:
    """D (nm) and / or es (%); the one not set has no broadening of its kind."""
    _check_angle(two_theta)
    if size is None and strain is None:
        raise InvalidInput("set D and / or es")
    d = size if size is not None else INFINITE
    e = strain if strain is not None else ZERO
    if round_inputs:
        d, e = round_size(d).quantity, round_strain(e).quantity
    ws, we = size_width(d, two_theta, instrument), strain_width(e, two_theta, instrument)
    return Estimate(
        Origin.MICROSTRUCTURE,
        two_theta,
        d,
        e,
        Broadening(ws, we, total_width(profile, ws, we)),
        rounded=round_inputs,
    )


def from_widths(
    size_part: Quantity | None,
    strain_part: Quantity | None,
    two_theta: Quantity,
    instrument: Instrument,
    profile: Profile,
    *,
    round_results: bool = False,
) -> Estimate:
    """FWHM_size and / or FWHM_strain (deg) -> D, es and the total width."""
    _check_angle(two_theta)
    if size_part is None and strain_part is None:
        raise InvalidInput("set FWHM_size and / or FWHM_strain")
    ws = size_part if size_part is not None else ZERO
    we = strain_part if strain_part is not None else ZERO
    th, dth = math.radians(two_theta.value / 2.0), math.radians(two_theta.esd / 2.0)
    d, e = INFINITE, ZERO
    if ws.is_positive:
        value = (
            instrument.k_size
            * instrument.wavelength_nm
            / (math.radians(ws.value) * math.cos(th))
        )
        d = Quantity(value, value * math.hypot(ws.esd / ws.value, dth * math.tan(th)))
    if we.is_positive:
        value = math.radians(we.value) / (instrument.k_strain * math.tan(th)) * 100.0
        e = Quantity(
            value,
            value * math.hypot(we.esd / we.value, dth / (math.cos(th) * math.sin(th))),
        )
    if round_results:
        d, e = round_size(d).quantity, round_strain(e).quantity
    return Estimate(
        Origin.WIDTHS,
        two_theta,
        d,
        e,
        Broadening(ws, we, total_width(profile, ws, we)),
        rounded=round_results,
    )


def from_densities(
    size_part: Quantity | None,
    strain_part: Quantity | None,
    two_theta: Quantity,
    instrument: Instrument,
    dislocations: DislocationSettings,
    *,
    round_values: bool = False,
) -> Estimate:
    """Ldis_D -> D (es = 0) and Ldis_es -> es (D = infinity), each with its own width."""
    _check_angle(two_theta)
    if size_part is None and strain_part is None:
        raise InvalidInput("set Ldis_D and / or Ldis_es")
    s = dislocations
    b = s.burgers.vector()
    if round_values:
        b = round_burgers(b).quantity
    d = e = None
    if size_part is not None and size_part.is_positive:
        value = math.sqrt(1e14 * s.distribution.coeff * s.n / size_part.value)
        d = Quantity(value, value * size_part.esd / (2.0 * size_part.value))
    if strain_part is not None and strain_part.is_positive:
        if not b.is_positive:
            raise InvalidInput("the Burgers vector b must be > 0 to estimate es")
        value = math.sqrt(1e-10 * strain_part.value * s.n / s.k) * b.value
        e = Quantity(
            value,
            value
            * math.hypot(strain_part.esd / (2.0 * strain_part.value), b.esd / b.value),
        )
    if round_values:
        d = round_size(d).quantity if d is not None else None
        e = round_strain(e).quantity if e is not None else None
    ws = size_width(d, two_theta, instrument) if d is not None else None
    we = strain_width(e, two_theta, instrument) if e is not None else None
    return Estimate(
        Origin.DENSITIES,
        two_theta,
        d,
        e,
        Broadening(ws, we, None),
        burgers=b,
        rounded=round_values,
    )
