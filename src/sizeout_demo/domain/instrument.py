"""The radiation and the constants of the broadening equations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from sizeout_demo.domain.errors import InvalidInput

#: Cu K-alpha-1, Angstrom.
CU_KA1 = 1.540598


class Profile(Enum):
    """The shape of the reflections; it decides how the two broadenings add up."""

    LORENTZ = "Lorentz"
    GAUSS = "Gauss"
    PSEUDO_VOIGT = "pseudo-Voigt"

    @property
    def short(self) -> str:
        return {"Lorentz": "Lor", "Gauss": "Gau", "pseudo-Voigt": "pV"}[self.value]


class Technique(Enum):
    """The straight-line plot the size and the strain are read from."""

    WHP = "Williamson-Hall plot"
    SSP = "Size-strain plot"

    @property
    def short(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class Instrument:
    """Wavelength in Angstrom; K_size (Scherrer) and K_strain of the WHP/SSP equations."""

    wavelength: float = CU_KA1
    k_size: float = 0.94
    k_strain: float = 4.0

    def __post_init__(self) -> None:
        for name, value in (
            ("wavelength", self.wavelength),
            ("K_size", self.k_size),
            ("K_strain", self.k_strain),
        ):
            if not (math.isfinite(value) and value > 0.0):
                raise InvalidInput(f"{name} must be a number > 0")

    @property
    def wavelength_nm(self) -> float:
        return self.wavelength / 10.0
