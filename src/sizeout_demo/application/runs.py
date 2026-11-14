"""Finished calculations, with everything needed to report them."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sizeout_demo.domain import (
    AnalysisSettings,
    DislocationSettings,
    Estimate,
    Instrument,
    Origin,
    Point,
    Profile,
    Quantity,
    Reflection,
    Solution,
    TechniqueResult,
)


@dataclass(frozen=True, slots=True)
class ReflectionData:
    title: str
    reflections: tuple[Reflection, ...]


@dataclass(frozen=True, slots=True)
class LoadedReflections:
    source: Path
    data: ReflectionData


@dataclass(frozen=True, slots=True)
class FitRun:
    """Reflections -> a line per technique -> D, es (and densities)."""

    source: Path
    title: str
    reflections: tuple[Reflection, ...]
    settings: AnalysisSettings
    results: tuple[TechniqueResult, ...]


class LineEntry(Enum):
    COEFFICIENTS = "coefficients A, B of the line"
    TWO_REFLECTIONS = "two reflections"


@dataclass(frozen=True, slots=True)
class LineRun:
    """A line typed in (or drawn through two points) -> D, es."""

    entry: LineEntry
    settings: AnalysisSettings
    result: TechniqueResult
    points: tuple[Point, Point] | None = None


@dataclass(frozen=True, slots=True)
class MicrostructureRun:
    """D and es typed in -> dislocation densities."""

    solution: Solution
    dislocations: DislocationSettings


@dataclass(frozen=True, slots=True)
class EstimateRequest:
    """One group of the calculator; ``first`` / ``second`` are size / strain values."""

    origin: Origin
    first: Quantity | None
    second: Quantity | None
    two_theta: Quantity
    hkl: tuple[int, int, int] | None
    instrument: Instrument
    profile: Profile
    dislocations: DislocationSettings | None
    rounded: bool


@dataclass(frozen=True, slots=True)
class EstimateRun:
    request: EstimateRequest
    estimate: Estimate


Run = FitRun | LineRun | MicrostructureRun | EstimateRun
