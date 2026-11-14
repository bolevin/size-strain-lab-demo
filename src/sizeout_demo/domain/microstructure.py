"""Crystallite size and microstrain, and the reference models for the degenerate lines.

A coefficient <= 0 is not an error: it says that one of the two broadenings is
absent.  The value that is left then comes from a model fitted under that very
assumption (the author's rules):

* no strain (the strain coefficient <= 0): e = 0, D from the es = 0 model -
  Scherrer and / or Monshi-Scherrer; two models entered give two solutions;
* no size broadening (the size coefficient <= 0): D is infinite, e from the
  D = infinity model of Stokes - Wilson;
* both: D infinite and e = 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from sizeout_demo.domain.errors import InvalidInput, ReferenceModelRequired
from sizeout_demo.domain.quantity import INFINITE, ZERO, Quantity


class Source(Enum):
    """Where a value of the solution comes from."""

    LINE = "the line"
    SCHERRER = "Scherrer model (es = 0)"
    MONSHI = "Monshi-Scherrer model (es = 0)"
    STOKES = "Stokes-Wilson model (D = infinity)"
    ABSENT = "no broadening of this kind"


@dataclass(frozen=True, slots=True)
class ReferenceModels:
    """D0 (nm) of the es = 0 models and es_inf (%) of the D = infinity model."""

    scherrer: Quantity | None = None
    monshi: Quantity | None = None
    stokes: Quantity | None = None

    def __post_init__(self) -> None:
        for name, model in (
            ("D0 (Scherrer)", self.scherrer),
            ("D0 (Monshi)", self.monshi),
            ("es_inf (Stokes)", self.stokes),
        ):
            if model is not None and not (model.value > 0.0 and math.isfinite(model.value)):
                raise InvalidInput(f"{name} must be a finite number > 0")

    @property
    def size_models(self) -> tuple[tuple[Source, Quantity], ...]:
        pairs = ((Source.SCHERRER, self.scherrer), (Source.MONSHI, self.monshi))
        return tuple((source, model) for source, model in pairs if model is not None)


@dataclass(frozen=True, slots=True)
class SizeStrain:
    """D in nm (infinite: no size broadening) and e in % (0: no strain)."""

    size: Quantity
    strain: Quantity
    size_source: Source = Source.LINE
    strain_source: Source = Source.LINE

    def __post_init__(self) -> None:
        if not self.size.value > 0.0:
            raise InvalidInput("the crystallite size D must be > 0 (or infinite)")
        if not (self.strain.value >= 0.0 and math.isfinite(self.strain.value)):
            raise InvalidInput("the microstrain es must be a finite number >= 0")

    @property
    def infinite(self) -> bool:
        return self.size.is_infinite

    @property
    def strained(self) -> bool:
        return self.strain.value > 0.0


def solutions(
    size: Quantity | None, strain: Quantity | None, references: ReferenceModels
) -> tuple[SizeStrain, ...]:
    """Apply the rules above to the (D, e) a line gave; None = that broadening is absent."""
    if size is None and strain is None:
        return (SizeStrain(INFINITE, ZERO, Source.ABSENT, Source.ABSENT),)
    if strain is None:
        if not references.size_models:
            raise ReferenceModelRequired(
                "The strain coefficient is <= 0, so there is no strain; the size then "
                "comes from an es = 0 model - enter D0 of Scherrer and / or Monshi."
            )
        return tuple(
            SizeStrain(d0, ZERO, source, Source.ABSENT)
            for source, d0 in references.size_models
        )
    if size is None:
        if references.stokes is None:
            raise ReferenceModelRequired(
                "The size coefficient is <= 0, so the crystallites are infinite; the "
                "strain then comes from the D = infinity model - enter es_inf of Stokes."
            )
        return (SizeStrain(INFINITE, references.stokes, Source.ABSENT, Source.STOKES),)
    return (SizeStrain(size, strain),)
