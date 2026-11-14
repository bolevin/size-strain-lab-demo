"""Six ways to turn reflection widths into a straight line - one interface (strategy).

Every reflection is broadened by the small size of the crystallites and by the
microstrain inside them:

    beta_size   = K_size * lambda / (D * cos theta)        (Scherrer)
    beta_strain = K_strain * e * tan theta                  (Stokes - Wilson)

How the two add up depends on the profile: Lorentz widths add, Gauss widths add in
quadrature, and for the pseudo-Voigt beta = beta_size + beta_strain^2 / beta.  Each
technique rearranges that sum into y = A + B*x, so that D comes from one coefficient
and e from the other:

    WHP  (Williamson-Hall)   D from A,  e from B
    SSP  (size-strain plot)  D from B,  e from A

``D`` is in nm (lambda is converted from Angstrom), ``e`` is reported in %.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from typing import ClassVar

from sizeout_demo.domain.instrument import Instrument, Profile, Technique
from sizeout_demo.domain.quantity import Quantity
from sizeout_demo.domain.reflection import Reflection
from sizeout_demo.domain.regression import Line

Transform = Callable[[Quantity, float], Quantity]


def _reciprocal(c: Quantity, scale: float) -> Quantity:  # c = scale / value
    value = scale / c.value
    return Quantity(value, value * c.esd / c.value)


def _reciprocal_root(c: Quantity, scale: float) -> Quantity:  # c = (scale / value)^2
    value = scale / math.sqrt(c.value)
    return Quantity(value, value * c.esd / (2.0 * c.value))


def _linear(c: Quantity, scale: float) -> Quantity:  # c = value / scale
    return Quantity(scale * c.value, scale * c.esd)


def _root(c: Quantity, scale: float) -> Quantity:  # c = (value / scale)^2
    value = scale * math.sqrt(c.value)
    return Quantity(value, value * c.esd / (2.0 * c.value))


# Lorentz keeps both terms linear, Gauss squares both, pseudo-Voigt squares the strain.
_SIZE: Mapping[Profile, Transform] = {
    Profile.LORENTZ: _reciprocal,
    Profile.GAUSS: _reciprocal_root,
    Profile.PSEUDO_VOIGT: _reciprocal,
}
_STRAIN: Mapping[Profile, Transform] = {
    Profile.LORENTZ: _linear,
    Profile.GAUSS: _root,
    Profile.PSEUDO_VOIGT: _root,
}


class Linearization(ABC):
    """A plot: where a reflection goes, and what the line's coefficients mean."""

    technique: ClassVar[Technique]
    profile: ClassVar[Profile]
    x_label: ClassVar[str]
    y_label: ClassVar[str]

    @abstractmethod
    def point(self, reflection: Reflection, instrument: Instrument) -> tuple[float, float]:
        """The reflection's (x, y) on this plot."""

    @abstractmethod
    def size_coefficient(self, line: Line) -> Quantity: ...

    @abstractmethod
    def strain_coefficient(self, line: Line) -> Quantity: ...

    @abstractmethod
    def size_from(self, coefficient: Quantity, instrument: Instrument) -> Quantity:
        """D (nm) from a positive size coefficient."""

    @abstractmethod
    def strain_from(self, coefficient: Quantity, instrument: Instrument) -> Quantity:
        """e (%) from a positive strain coefficient."""

    def microstructure(
        self, line: Line, instrument: Instrument
    ) -> tuple[Quantity | None, Quantity | None]:
        """(D, e) read from the line.

        None where the coefficient is <= 0: for the size that is "no size
        broadening" (the infinite crystallite), for the strain "no strain".
        """
        cd, ce = self.size_coefficient(line), self.strain_coefficient(line)
        size = self.size_from(cd, instrument) if cd.value > 0.0 else None
        strain = self.strain_from(ce, instrument) if ce.value > 0.0 else None
        return size, strain


class _WilliamsonHall(Linearization):
    technique = Technique.WHP

    def size_coefficient(self, line: Line) -> Quantity:
        return line.intercept

    def strain_coefficient(self, line: Line) -> Quantity:
        return line.slope

    def size_from(self, coefficient: Quantity, instrument: Instrument) -> Quantity:
        return _SIZE[self.profile](
            coefficient, instrument.k_size * instrument.wavelength_nm
        )

    def strain_from(self, coefficient: Quantity, instrument: Instrument) -> Quantity:
        return _STRAIN[self.profile](coefficient, 100.0)


class _SizeStrain(Linearization):
    technique = Technique.SSP

    def size_coefficient(self, line: Line) -> Quantity:
        return line.slope

    def strain_coefficient(self, line: Line) -> Quantity:
        return line.intercept

    def size_from(self, coefficient: Quantity, instrument: Instrument) -> Quantity:
        return _SIZE[self.profile](coefficient, 1.0)

    def strain_from(self, coefficient: Quantity, instrument: Instrument) -> Quantity:
        return _STRAIN[self.profile](coefficient, 200.0 / instrument.k_strain)

    @staticmethod
    def _reduced(reflection: Reflection, instrument: Instrument) -> tuple[float, float]:
        """(d, d * beta * cos theta / lambda), d and lambda in nm."""
        lam = instrument.wavelength_nm
        d = reflection.d_spacing(lam)
        return d, d * reflection.beta * math.cos(reflection.theta) / lam


class WhpLorentz(_WilliamsonHall):
    """beta cos = K lambda / D + e * K_strain sin."""

    profile = Profile.LORENTZ
    x_label = "Kε·sinθ"
    y_label = "β·cosθ"

    def point(self, reflection: Reflection, instrument: Instrument) -> tuple[float, float]:
        th = reflection.theta
        return instrument.k_strain * math.sin(th), reflection.beta * math.cos(th)


class WhpGauss(_WilliamsonHall):
    """(beta cos)^2 = (K lambda / D)^2 + e^2 (K_strain sin)^2."""

    profile = Profile.GAUSS
    x_label = "(Kε·sinθ)²"
    y_label = "(β·cosθ)²"

    def point(self, reflection: Reflection, instrument: Instrument) -> tuple[float, float]:
        th = reflection.theta
        return (
            (instrument.k_strain * math.sin(th)) ** 2,
            (reflection.beta * math.cos(th)) ** 2,
        )


class WhpPseudoVoigt(_WilliamsonHall):
    """beta cos = K lambda / D + e^2 (K_strain sin)^2 / (beta cos)."""

    profile = Profile.PSEUDO_VOIGT
    x_label = "(Kε·sinθ)² / (β·cosθ)"
    y_label = "β·cosθ"

    def point(self, reflection: Reflection, instrument: Instrument) -> tuple[float, float]:
        th = reflection.theta
        y = reflection.beta * math.cos(th)
        return (instrument.k_strain * math.sin(th)) ** 2 / y, y


class SspLorentz(_SizeStrain):
    """d beta cos / lambda = (1/D) * K d + K_strain e / 2."""

    profile = Profile.LORENTZ
    x_label = "K·d, nm"
    y_label = "d·β·cosθ / λ"

    def point(self, reflection: Reflection, instrument: Instrument) -> tuple[float, float]:
        d, reduced = self._reduced(reflection, instrument)
        return instrument.k_size * d, reduced


class SspGauss(_SizeStrain):
    """(d beta cos / lambda)^2 = (1/D^2) (K d)^2 + (K_strain e / 2)^2."""

    profile = Profile.GAUSS
    x_label = "(K·d)², nm²"
    y_label = "(d·β·cosθ / λ)²"

    def point(self, reflection: Reflection, instrument: Instrument) -> tuple[float, float]:
        d, reduced = self._reduced(reflection, instrument)
        return (instrument.k_size * d) ** 2, reduced**2


class SspPseudoVoigt(_SizeStrain):
    """(d beta cos / lambda)^2 = (1/D) K d^2 beta cos / lambda + (K_strain e / 2)^2."""

    profile = Profile.PSEUDO_VOIGT
    x_label = "K·d²·β·cosθ / λ, nm"
    y_label = "(d·β·cosθ / λ)²"

    def point(self, reflection: Reflection, instrument: Instrument) -> tuple[float, float]:
        d, reduced = self._reduced(reflection, instrument)
        return instrument.k_size * d * reduced, reduced**2


LINEARIZATIONS: Mapping[tuple[Technique, Profile], Linearization] = {
    (cls.technique, cls.profile): cls()
    for cls in (WhpLorentz, WhpGauss, WhpPseudoVoigt, SspLorentz, SspGauss, SspPseudoVoigt)
}


def linearization(technique: Technique, profile: Profile) -> Linearization:
    return LINEARIZATIONS[(technique, profile)]
