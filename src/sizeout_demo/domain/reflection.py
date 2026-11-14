"""One diffraction reflection: its position and its width without the instrument."""

from __future__ import annotations

import math
from dataclasses import dataclass

from sizeout_demo.domain.errors import InvalidInput


@dataclass(frozen=True, slots=True)
class Reflection:
    """2Theta and the instrument-corrected FWHM, both in degrees."""

    two_theta: float
    fwhm: float
    hkl: tuple[int, int, int] | None = None
    use: bool = True

    def __post_init__(self) -> None:
        if not (math.isfinite(self.two_theta) and 0.0 < self.two_theta < 180.0):
            raise InvalidInput(f"2Theta = {self.two_theta} must lie between 0 and 180 deg")
        if not (math.isfinite(self.fwhm) and self.fwhm > 0.0):
            raise InvalidInput(
                f"FWHM = {self.fwhm} at 2Theta = {self.two_theta} must be > 0"
            )

    @property
    def theta(self) -> float:
        """The Bragg angle in radians."""
        return math.radians(self.two_theta / 2.0)

    @property
    def beta(self) -> float:
        """The width in radians."""
        return math.radians(self.fwhm)

    def d_spacing(self, wavelength_nm: float) -> float:
        """Bragg's law, d = lambda / (2 sin theta), in the unit of the wavelength."""
        return wavelength_nm / (2.0 * math.sin(self.theta))

    @property
    def label(self) -> str:
        return "".join(str(i) for i in self.hkl) if self.hkl else ""

    def toggled(self) -> Reflection:
        return Reflection(self.two_theta, self.fwhm, self.hkl, not self.use)
