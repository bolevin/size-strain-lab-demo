"""The use cases: load reflections, calculate in one of four ways, export."""

from __future__ import annotations

from pathlib import Path

from sizeout_demo.application.ports import (
    ReflectionReader,
    ReportRenderer,
    TableRenderer,
    TextStore,
)
from sizeout_demo.application.runs import (
    EstimateRequest,
    EstimateRun,
    FitRun,
    LineEntry,
    LineRun,
    LoadedReflections,
    MicrostructureRun,
    Run,
)
from sizeout_demo.domain import (
    AnalysisSettings,
    DislocationSettings,
    InvalidInput,
    Line,
    Origin,
    Point,
    Reflection,
    SizeStrain,
    Technique,
    analyse_reflections,
    from_densities,
    from_microstructure,
    from_widths,
    line_through,
    solve,
    with_densities,
)


class SizeStrainService:
    """Holds no state: every call says what it works on."""

    def __init__(
        self,
        reader: ReflectionReader,
        report: ReportRenderer,
        table: TableRenderer,
        store: TextStore,
    ) -> None:
        self._reader = reader
        self._report = report
        self._table = table
        self._store = store

    # ---- the four calculations -------------------------------------------
    def load(self, path: Path) -> LoadedReflections:
        return LoadedReflections(source=path, data=self._reader.read(path))

    def fit(
        self,
        loaded: LoadedReflections,
        settings: AnalysisSettings,
        reflections: tuple[Reflection, ...] | None = None,
    ) -> FitRun:
        """Fit the loaded reflections - or the edited copy of them the user selected."""
        chosen = loaded.data.reflections if reflections is None else reflections
        return FitRun(
            loaded.source,
            loaded.data.title,
            chosen,
            settings,
            analyse_reflections(chosen, settings),
        )

    def from_line(
        self, line: Line, technique: Technique, settings: AnalysisSettings
    ) -> LineRun:
        return LineRun(LineEntry.COEFFICIENTS, settings, solve(line, technique, settings))

    def from_two_reflections(
        self, first: Point, second: Point, technique: Technique, settings: AnalysisSettings
    ) -> LineRun:
        line = line_through(first, second)
        return LineRun(
            LineEntry.TWO_REFLECTIONS,
            settings,
            solve(line, technique, settings),
            (first, second),
        )

    def from_microstructure(
        self, microstructure: SizeStrain, dislocations: DislocationSettings
    ) -> MicrostructureRun:
        return MicrostructureRun(with_densities(microstructure, dislocations), dislocations)

    def estimate(self, request: EstimateRequest) -> EstimateRun:
        r = request
        if r.origin is Origin.MICROSTRUCTURE:
            estimate = from_microstructure(
                r.first,
                r.second,
                r.two_theta,
                r.instrument,
                r.profile,
                round_inputs=r.rounded,
            )
        elif r.origin is Origin.WIDTHS:
            estimate = from_widths(
                r.first,
                r.second,
                r.two_theta,
                r.instrument,
                r.profile,
                round_results=r.rounded,
            )
        else:
            if r.dislocations is None:
                raise InvalidInput(
                    "estimating from the densities needs the dislocation parameters"
                )
            estimate = from_densities(
                r.first,
                r.second,
                r.two_theta,
                r.instrument,
                r.dislocations,
                round_values=r.rounded,
            )
        return EstimateRun(request, estimate)

    # ---- output ----------------------------------------------------------
    def report(self, run: Run) -> str:
        return self._report.render(run)

    def table(self, run: Run) -> str:
        return self._table.render(run)

    def export_report(self, run: Run, path: Path) -> None:
        self._store.save(path, self._report.render(run))

    def export_table(self, run: Run, path: Path) -> None:
        self._store.save(path, self._table.render(run))
