"""A value with its estimated standard deviation (e.s.d.)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from sizeout_demo.domain.errors import InvalidInput


@dataclass(frozen=True, slots=True)
class Quantity:
    """``value`` may be infinite (the infinite crystallite); the e.s.d. may not."""

    value: float
    esd: float = 0.0

    def __post_init__(self) -> None:
        if math.isnan(self.value):
            raise InvalidInput("a value must be a number")
        if not (math.isfinite(self.esd) and self.esd >= 0.0):
            raise InvalidInput("an e.s.d. must be a finite number >= 0")

    @property
    def is_infinite(self) -> bool:
        return math.isinf(self.value)

    @property
    def is_positive(self) -> bool:
        return self.value > 0.0

    def __str__(self) -> str:
        return f"{self.value:.6g} +- {self.esd:.2g}"


ZERO = Quantity(0.0)
INFINITE = Quantity(math.inf)
