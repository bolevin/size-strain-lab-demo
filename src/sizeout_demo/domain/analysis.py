"""The calculations as pure functions: reflections or a line in, solutions out."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from sizeout_demo.domain.dislocations import Densities, DislocationSettings, densities
from sizeout_demo.domain.errors import InsufficientData, ReferenceModelRequired
from sizeout_demo.domain.instrument import Instrument, Profile, Technique
from sizeout_demo.domain.linearization import linearization
from sizeout_demo.domain.microstructure import ReferenceModels, SizeStrain, solutions
from sizeout_demo.domain.reflection import Reflection
from sizeout_demo.domain.regression import MIN_FIT_POINTS, Line, fit_line


@dataclass(frozen=True, slots=True)
class AnalysisSettings:
    instrument: Instrument = field(default_factory=Instrument)
    profile: Profile = Profile.PSEUDO_VOIGT
    references: ReferenceModels = field(default_factory=ReferenceModels)
    dislocations: DislocationSettings | None = None


@dataclass(frozen=True, slots=True)
class PlotPoint:
    x: float
    y: float
    used: bool
    label: str


@dataclass(frozen=True, slots=True)
class Solution:
    microstructure: SizeStrain
    densities: Densities | None = None


@dataclass(frozen=True, slots=True)
class TechniqueResult:
    technique: Technique
    profile: Profile
    line: Line
    solutions: tuple[Solution, ...]
    points: tuple[PlotPoint, ...] = ()
    problem: str = ""  # why there is no solution (a model is missing)


def solve(line: Line, technique: Technique, settings: AnalysisSettings) -> TechniqueResult:
    """D and es from a line - fitted here, typed in, or drawn through two reflections."""
    plot = linearization(technique, settings.profile)
    size, strain = plot.microstructure(line, settings.instrument)
    try:
        found = solutions(size, strain, settings.references)
    except ReferenceModelRequired as missing:
        return TechniqueResult(technique, settings.profile, line, (), problem=str(missing))
    return TechniqueResult(
        technique,
        settings.profile,
        line,
        tuple(with_densities(m, settings.dislocations) for m in found),
    )


def with_densities(
    microstructure: SizeStrain, dislocations: DislocationSettings | None
) -> Solution:
    if dislocations is None:
        return Solution(microstructure)
    return Solution(microstructure, densities(microstructure, dislocations))


def analyse_reflections(
    reflections: Sequence[Reflection],
    settings: AnalysisSettings,
    techniques: Sequence[Technique] = (Technique.WHP, Technique.SSP),
) -> tuple[TechniqueResult, ...]:
    """Per technique: plot the reflections, fit the line through the used ones, solve."""
    used = [r for r in reflections if r.use]
    if len(used) < MIN_FIT_POINTS:
        raise InsufficientData(
            f"{len(used)} reflection(s) selected: the fit needs at least {MIN_FIT_POINTS}"
        )
    results = []
    for technique in techniques:
        plot = linearization(technique, settings.profile)
        points = tuple(
            PlotPoint(*plot.point(r, settings.instrument), used=r.use, label=r.label)
            for r in reflections
        )
        chosen = [p for p in points if p.used]
        line = fit_line([p.x for p in chosen], [p.y for p in chosen])
        result = solve(line, technique, settings)
        results.append(
            TechniqueResult(
                result.technique,
                result.profile,
                result.line,
                result.solutions,
                points,
                result.problem,
            )
        )
    return tuple(results)
