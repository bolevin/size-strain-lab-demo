"""The whole fit: both techniques, unused reflections, a missing model."""

from __future__ import annotations

import pytest

from sizeout_demo.application import ReflectionData
from sizeout_demo.domain import (
    AnalysisSettings,
    DislocationSettings,
    InsufficientData,
    Line,
    Quantity,
    ReferenceModels,
    Reflection,
    Technique,
    analyse_reflections,
    solve,
)


def test_both_techniques_on_the_sample(sample: ReflectionData) -> None:
    whp, ssp = analyse_reflections(sample.reflections, AnalysisSettings())
    assert (whp.technique, ssp.technique) == (Technique.WHP, Technique.SSP)
    for result in (whp, ssp):
        assert len(result.points) == 9  # every reflection is plotted
        assert sum(p.used for p in result.points) == 8  # 331 is left out of the fit
        assert result.line.n_points == 8
        (solution,) = result.solutions
        # the sample was made with D = 45 nm, es = 0.12 % and 2.5 % noise
        assert 40.0 < solution.microstructure.size.value < 50.0
        assert 0.10 < solution.microstructure.strain.value < 0.14
        assert solution.densities is None


def test_leaving_a_reflection_out_changes_the_fit(sample: ReflectionData) -> None:
    all_used = tuple(Reflection(r.two_theta, r.fwhm, r.hkl) for r in sample.reflections)
    with_331 = analyse_reflections(all_used, AnalysisSettings())[0]
    without = analyse_reflections(sample.reflections, AnalysisSettings())[0]
    assert with_331.line.n_points == 9
    assert with_331.line.r_squared is not None
    assert without.line.r_squared is not None
    assert with_331.line.r_squared < without.line.r_squared  # the faulted one is off-line


def test_densities_are_attached_when_asked(sample: ReflectionData) -> None:
    settings = AnalysisSettings(dislocations=DislocationSettings())
    for result in analyse_reflections(sample.reflections, settings):
        assert result.solutions[0].densities is not None


def test_too_few_used_reflections() -> None:
    reflections = [
        Reflection(40.0, 0.3),
        Reflection(60.0, 0.4),
        Reflection(80.0, 0.5, use=False),
    ]
    with pytest.raises(InsufficientData, match="2 reflection"):
        analyse_reflections(reflections, AnalysisSettings())


def test_a_missing_model_is_reported_per_technique_not_raised() -> None:
    line = Line(Quantity(3.3e-3, 1e-4), Quantity(-2e-7, 1e-7))  # WHP: no strain
    result = solve(line, Technique.WHP, AnalysisSettings())
    assert result.solutions == ()
    assert "D0 of Scherrer" in result.problem
    found = solve(
        line,
        Technique.WHP,
        AnalysisSettings(references=ReferenceModels(scherrer=Quantity(44.0, 1.5))),
    )
    assert found.solutions[0].microstructure.size == Quantity(44.0, 1.5)
