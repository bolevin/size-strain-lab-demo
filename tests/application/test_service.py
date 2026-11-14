"""The use cases with every port replaced by a fake: no file is touched."""

from __future__ import annotations

from pathlib import Path

import pytest

from sizeout_demo.application import (
    EstimateRequest,
    FitRun,
    ReflectionData,
    Run,
    SizeStrainService,
)
from sizeout_demo.domain import (
    AnalysisSettings,
    Instrument,
    InvalidInput,
    Origin,
    Profile,
    Quantity,
    Reflection,
)

DATA = ReflectionData(
    "fake",
    (
        Reflection(40.0, 0.30),
        Reflection(60.0, 0.38),
        Reflection(80.0, 0.49),
        Reflection(100.0, 0.66),
    ),
)


class FakeReader:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def read(self, path: Path) -> ReflectionData:
        self.paths.append(path)
        return DATA


class FakeRenderer:
    def __init__(self, tag: str) -> None:
        self.tag = tag

    def render(self, run: Run) -> str:
        return f"{self.tag}:{type(run).__name__}"


class FakeStore:
    def __init__(self) -> None:
        self.saved: dict[Path, str] = {}

    def save(self, path: Path, text: str) -> None:
        self.saved[path] = text


@pytest.fixture
def parts() -> tuple[FakeReader, FakeStore, SizeStrainService]:
    reader, store = FakeReader(), FakeStore()
    return (
        reader,
        store,
        SizeStrainService(reader, FakeRenderer("report"), FakeRenderer("table"), store),
    )


def test_load_fit_and_export(
    parts: tuple[FakeReader, FakeStore, SizeStrainService],
) -> None:
    reader, store, service = parts
    loaded = service.load(Path("x.csv"))
    assert reader.paths == [Path("x.csv")]
    run = service.fit(loaded, AnalysisSettings())
    assert isinstance(run, FitRun)
    assert len(run.results) == 2
    service.export_report(run, Path("r.txt"))
    service.export_table(run, Path("t.csv"))
    assert store.saved == {Path("r.txt"): "report:FitRun", Path("t.csv"): "table:FitRun"}


def test_fit_uses_the_edited_selection(
    parts: tuple[FakeReader, FakeStore, SizeStrainService],
) -> None:
    _, _, service = parts
    loaded = service.load(Path("x.csv"))
    edited = (*DATA.reflections[:3], DATA.reflections[3].toggled())
    run = service.fit(loaded, AnalysisSettings(), edited)
    assert run.results[0].line.n_points == 3
    assert run.reflections == edited


def test_estimate_from_densities_needs_the_dislocation_parameters(
    parts: tuple[FakeReader, FakeStore, SizeStrainService],
) -> None:
    _, _, service = parts
    request = EstimateRequest(
        Origin.DENSITIES,
        Quantity(1e11),
        None,
        Quantity(40.0),
        None,
        Instrument(),
        Profile.LORENTZ,
        None,
        rounded=False,
    )
    with pytest.raises(InvalidInput, match="dislocation parameters"):
        service.estimate(request)
