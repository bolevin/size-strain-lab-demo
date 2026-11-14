"""Dislocation density from the size and the strain.

Williamson & Smallman (1956):

    Ldis_D  = 1e14 * Coeff * n / D^2            (D in nm; 1/cm^2)
    Ldis_es = 1e10 * (k / n) * (es / b)^2       (es in %, b in nm)
    Ldis    = sqrt(Ldis_D * Ldis_es) = Cf * es / (b * D),   Cf = sqrt(k * Coeff)

n - dislocations at the crystallite boundary, Coeff - 1 for an isotropic and 3 for
an anisotropic distribution, k - between 6/pi (Gauss) and 24 (Cauchy) depending on
the strain distribution, b - the Burgers vector.

Ashby (1970), the additive model: Ro_total = Ro_GND + Ro_SSD = Ldis_D + Ldis_es.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from sizeout_demo.domain.errors import InvalidInput
from sizeout_demo.domain.microstructure import SizeStrain
from sizeout_demo.domain.quantity import ZERO, Quantity
from sizeout_demo.domain.rounding import Rounded, round_burgers, round_size, round_strain

K_GAUSS = 6.0 / math.pi
K_CAUCHY = 24.0


class Distribution(Enum):
    ISOTROPIC = 1
    ANISOTROPIC = 3

    @property
    def coeff(self) -> int:
        return self.value

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass(frozen=True, slots=True)
class EnteredBurgers:
    """|b| typed in, nm."""

    b: Quantity

    def __post_init__(self) -> None:
        if self.b.value < 0.0 or self.b.is_infinite:
            raise InvalidInput("the Burgers vector b must be a finite number >= 0")

    def vector(self) -> Quantity:
        return self.b


@dataclass(frozen=True, slots=True)
class CubicBurgers:
    """b = a/m [u v w] of a cubic cell; a in Angstrom, |b| in nm."""

    a: Quantity
    m: int = 2
    uvw: tuple[int, int, int] = (1, -1, 0)

    def __post_init__(self) -> None:
        if not (self.a.value > 0.0 and math.isfinite(self.a.value)):
            raise InvalidInput("the cell parameter a must be a finite number > 0")
        if self.m < 1:
            raise InvalidInput("m of b = a/m [u v w] must be >= 1")
        if not any(self.uvw):
            raise InvalidInput("[u v w] = [0 0 0] gives no Burgers vector")

    def vector(self) -> Quantity:
        root = math.sqrt(sum(i * i for i in self.uvw))
        return Quantity(
            self.a.value / 10.0 / self.m * root, self.a.esd / 10.0 / self.m * root
        )


BurgersVector = EnteredBurgers | CubicBurgers


@dataclass(frozen=True, slots=True)
class DislocationSettings:
    n: float = 1.0
    distribution: Distribution = Distribution.ANISOTROPIC
    k: float = 12.0
    burgers: BurgersVector = field(default_factory=lambda: CubicBurgers(Quantity(4.0495)))
    round_inputs: bool = True  # D, es and b as published, before the densities

    def __post_init__(self) -> None:
        if not (math.isfinite(self.n) and self.n > 0.0):
            raise InvalidInput("n (dislocations at the crystallite boundary) must be > 0")
        if not K_GAUSS - 1e-9 <= self.k <= K_CAUCHY:
            raise InvalidInput("k must lie between 6/pi = 1.9099 (Gauss) and 24 (Cauchy)")


@dataclass(frozen=True, slots=True)
class Densities:
    """All in 1/cm^2.  The ``used_*`` are the values the densities were computed from."""

    size_part: Quantity  # Ldis_D  = Ro_GND
    strain_part: Quantity  # Ldis_es = Ro_SSD
    williamson: Quantity  # Ldis, the geometric mean
    ashby: Quantity  # Ro_total, the sum
    cf: float | None  # of Ldis = Cf es / (b D); None if not that product
    distribution: str  # "isotropic", "anisotropic", or "any"
    used_size: Rounded
    used_strain: Rounded
    used_burgers: Rounded


def _size_part(size: Quantity, s: DislocationSettings) -> Quantity:
    if size.is_infinite:
        return ZERO
    value = 1e14 * s.distribution.coeff * s.n / size.value**2
    return Quantity(value, 2.0 * value * size.esd / size.value)


def _strain_part(strain: Quantity, b: Quantity, s: DislocationSettings) -> Quantity:
    if not strain.is_positive:
        return ZERO
    if not b.is_positive:
        raise InvalidInput("the Burgers vector b must be > 0 when there is strain")
    value = 1e10 * s.k / s.n * (strain.value / b.value) ** 2
    return Quantity(
        value, 2.0 * value * math.hypot(strain.esd / strain.value, b.esd / b.value)
    )


def _geometric_mean(ld: Quantity, le: Quantity) -> Quantity:
    if ld.is_positive and le.is_positive:
        value = math.sqrt(ld.value * le.value)
        return Quantity(
            value, value * math.hypot(ld.esd / (2.0 * ld.value), le.esd / (2.0 * le.value))
        )
    return ld if ld.is_positive else le


def densities(microstructure: SizeStrain, settings: DislocationSettings) -> Densities:
    size, strain = microstructure.size, microstructure.strain
    b = settings.burgers.vector()
    if settings.round_inputs:
        used_size, used_strain, used_b = (
            round_size(size),
            round_strain(strain),
            round_burgers(b),
        )
    else:
        used_size, used_strain, used_b = (
            Rounded(size, None),
            Rounded(strain, None),
            Rounded(b, None),
        )
    ld = _size_part(used_size.quantity, settings)
    le = _strain_part(used_strain.quantity, used_b.quantity, settings)
    both = ld.is_positive and le.is_positive
    result = Densities(
        size_part=ld,
        strain_part=le,
        williamson=_geometric_mean(ld, le),
        ashby=Quantity(ld.value + le.value, math.hypot(ld.esd, le.esd)),
        cf=math.sqrt(settings.k * settings.distribution.coeff) if both else None,
        distribution="any"
        if le.is_positive and not ld.is_positive
        else settings.distribution.label,
        used_size=used_size,
        used_strain=used_strain,
        used_burgers=used_b,
    )
    if not all(math.isfinite(q.value) for q in (result.williamson, result.ashby)):
        raise InvalidInput("the density overflows - check n, k and b")
    return result
