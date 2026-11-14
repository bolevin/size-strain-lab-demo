"""Presenters: user intent -> use-case calls; results -> view models.  No Qt here."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from sizeout_demo.application import (
    EstimateRequest,
    FitRun,
    LineRun,
    LoadedReflections,
    MicrostructureRun,
    ReflectionFormatError,
    Run,
    SizeStrainService,
)
from sizeout_demo.application.formatting import (
    INFINITY,
    esd_text,
    number_text,
    power_text,
    size_text,
    strain_text,
)
from sizeout_demo.domain import (
    AnalysisSettings,
    DomainError,
    Line,
    Origin,
    Point,
    Quantity,
    Reflection,
    SizeStrain,
    Source,
    TechniqueResult,
    linearization,
)
from sizeout_demo.ui import parsing
from sizeout_demo.ui.view import (
    DataViewModel,
    EstimateView,
    FitView,
    LineMode,
    LineView,
    Metric,
    Notifier,
    PlotViewModel,
    ResultViewModel,
    RowViewModel,
    Tone,
)

EMPTY = "—"
_PROBLEMS = (ValueError, DomainError)  # parsing.InputError is a ValueError


def _microstructure_metrics(prefix: str, result: TechniqueResult) -> tuple[Metric, Metric]:
    if not result.solutions:
        return (
            Metric(f"{prefix}D, nm", EMPTY, "no solution"),
            Metric(f"{prefix}es, %", EMPTY, "no solution"),
        )
    m = result.solutions[0].microstructure
    r2 = "" if result.line.r_squared is None else f"R² = {result.line.r_squared:.4f}"
    size_hint = r2 if m.size_source is Source.LINE else m.size_source.value
    strain_hint = (
        f"{m.strain.value:.4g} ± {m.strain.esd:.2g}"
        if m.strain_source is Source.LINE
        else m.strain_source.value
    )
    return (
        Metric(f"{prefix}D, nm", size_text(m.size), size_hint),
        Metric(f"{prefix}es, %", strain_text(m.strain), strain_hint),
    )


def _notice(results: tuple[TechniqueResult, ...]) -> tuple[str, Tone]:
    notes = [f"{r.technique.short}: {r.problem}" for r in results if r.problem]
    notes += [
        f"{r.technique.short}: {len(r.solutions)} solutions, one per es = 0 model - "
        "the report lists both."
        for r in results
        if len(r.solutions) > 1
    ]
    return (" ".join(notes), Tone.WARNING) if notes else ("", Tone.NEUTRAL)


def _density_metric(results: tuple[TechniqueResult, ...]) -> Metric | None:
    for r in results:
        if r.solutions and r.solutions[0].densities is not None:
            d = r.solutions[0].densities
            return Metric(
                f"{r.technique.short} · Ldis, cm⁻²",
                power_text(d.williamson, 2),
                f"Ro_total {power_text(d.ashby, 2)}",
            )
    return None


def plot_view_model(result: TechniqueResult) -> PlotViewModel:
    plot = linearization(result.technique, result.profile)
    xs = tuple(p.x for p in result.points)
    line = result.line
    x1 = max(xs) * 1.06 if xs else 1.0
    r2 = "" if line.r_squared is None else f"     R² = {line.r_squared:.4f}"
    return PlotViewModel(
        title=f"{result.technique.value} · {result.profile.value}",
        x_label=plot.x_label,
        y_label=plot.y_label,
        xs=xs,
        ys=tuple(p.y for p in result.points),
        used=tuple(p.used for p in result.points),
        labels=tuple(p.label for p in result.points),
        line=(0.0, line.at(0.0), x1, line.at(x1)),
        equation=(
            f"y = {number_text(line.intercept.value, 4)} + "
            f"{number_text(line.slope.value, 4)}·x{r2}"
        ),
    )


class _Exports:
    """Save the report and the table of the last run - the same on every page."""

    _view: Notifier
    _service: SizeStrainService
    _run: Run | None
    _stem: str = "sizestrain"

    def save_report(self) -> None:
        self._export("report", ".txt", self._service.export_report)

    def export_table(self) -> None:
        self._export("table", ".csv", self._service.export_table)

    def _export(self, kind: str, suffix: str, action: Callable[[Run, Path], None]) -> None:
        if self._run is None:
            self._view.show_error("Nothing to save", "Run the calculation first.")
            return
        path = self._view.ask_save_path(self._suggested(suffix), kind)
        if path is None:
            return
        try:
            action(self._run, path)
        except OSError as error:
            self._view.show_error(f"Cannot save the {kind}", str(error))
            return
        self._view.show_success(f"{kind.capitalize()} saved", str(path))

    def _suggested(self, suffix: str) -> Path:
        return Path.home() / f"{self._stem}{suffix}"


class FitPresenter(_Exports):
    _view: FitView

    def __init__(self, view: FitView, service: SizeStrainService, sample: Path) -> None:
        self._view = view
        self._service = service
        self._sample = sample
        self._loaded: LoadedReflections | None = None
        self._reflections: tuple[Reflection, ...] = ()
        self._run: FitRun | None = None

    # ---- intents ---------------------------------------------------------
    def open_file(self) -> None:
        path = self._view.ask_open_path()
        if path is not None:
            self.load(path)

    def open_sample(self) -> None:
        self.load(self._sample)

    def load(self, path: Path) -> None:
        try:
            loaded = self._service.load(path)
        except (OSError, ReflectionFormatError, DomainError) as error:
            self._view.show_error(f"Cannot open {path.name}", str(error))
            return
        self._loaded, self._run = loaded, None
        self._reflections = loaded.data.reflections
        self._stem = path.stem + "_sizestrain"
        self._view.clear_result()
        self._show_data()

    def toggle(self, index: int) -> None:
        """Use a reflection or leave it out - from the table or a click on the plot."""
        if not 0 <= index < len(self._reflections):
            return
        items = list(self._reflections)
        items[index] = items[index].toggled()
        self._reflections = tuple(items)
        self._show_data()
        if self._run is not None:
            self.calculate()

    def calculate(self) -> None:
        if self._loaded is None:
            self._view.show_error("No reflections", "Open a reflection list first.")
            return
        try:
            settings = AnalysisSettings(
                instrument=parsing.instrument(self._view.instrument()),
                profile=self._view.instrument().profile,
                references=parsing.references(self._view.references()),
                dislocations=parsing.dislocations(self._view.dislocations()),
            )
            run = self._service.fit(self._loaded, settings, self._reflections)
        except _PROBLEMS as error:
            self._run = None
            self._view.clear_result()
            self._view.show_error("Cannot calculate", str(error))
            return
        self._run = run
        self._view.show_result(self._result_view_model(run))

    # ---- view models -----------------------------------------------------
    def _show_data(self) -> None:
        assert self._loaded is not None
        refl = self._reflections
        used = sum(r.use for r in refl)
        self._view.show_data(
            DataViewModel(
                file_name=self._loaded.source.name,
                title=self._loaded.data.title,
                summary=(
                    f"{len(refl)} reflections, {used} used, "
                    f"2θ {min(r.two_theta for r in refl):.1f} - "
                    f"{max(r.two_theta for r in refl):.1f}°"
                ),
                rows=tuple(
                    RowViewModel(
                        r.label or EMPTY, f"{r.two_theta:.4f}", f"{r.fwhm:.5f}", r.use
                    )
                    for r in refl
                ),
            )
        )

    def _result_view_model(self, run: FitRun) -> ResultViewModel:
        metrics: list[Metric] = []
        for result in run.results:
            metrics += _microstructure_metrics(f"{result.technique.short} · ", result)
        density = _density_metric(run.results)
        used = sum(r.use for r in run.reflections)
        metrics.append(
            density
            or Metric(
                "Reflections used",
                f"{used} of {len(run.reflections)}",
                "click a point to leave it out",
            )
        )
        notice, tone = _notice(run.results)
        return ResultViewModel(
            tuple(metrics),
            notice,
            tone,
            self._service.report(run),
            tuple(plot_view_model(r) for r in run.results),
        )


class LinePresenter(_Exports):
    """D and es from a line typed in, from two reflections, or typed in themselves."""

    _view: LineView

    def __init__(self, view: LineView, service: SizeStrainService) -> None:
        self._view = view
        self._service = service
        self._run: Run | None = None
        self._stem = "sizestrain_line"

    def calculate(self) -> None:
        try:
            run = self._calculate()
        except _PROBLEMS as error:
            self._run = None
            self._view.clear_result()
            self._view.show_error("Cannot calculate", str(error))
            return
        self._run = run
        self._view.show_result(self._result_view_model(run))

    def _calculate(self) -> Run:
        inp = self._view.line_input()
        settings = AnalysisSettings(
            instrument=parsing.instrument(self._view.instrument()),
            profile=self._view.instrument().profile,
            references=parsing.references(self._view.references()),
            dislocations=parsing.dislocations(self._view.dislocations()),
        )
        if inp.mode is LineMode.COEFFICIENTS:
            line = Line(
                parsing.required_pair(inp.intercept, "A"),
                parsing.required_pair(inp.slope, "B"),
            )
            return self._service.from_line(line, inp.technique, settings)
        if inp.mode is LineMode.TWO_REFLECTIONS:
            first = Point(
                parsing.required_pair(inp.x1, "x1"), parsing.required_pair(inp.y1, "y1")
            )
            second = Point(
                parsing.required_pair(inp.x2, "x2"), parsing.required_pair(inp.y2, "y2")
            )
            return self._service.from_two_reflections(
                first, second, inp.technique, settings
            )
        size = parsing.required_pair(inp.size, "D")
        strain = parsing.pair(inp.strain, "es") or Quantity(0.0)
        microstructure = SizeStrain(
            Quantity(float("inf")) if size.value == 0.0 else size, strain
        )
        dislocations = parsing.dislocations(self._view.dislocations(), force=True)
        assert dislocations is not None
        return self._service.from_microstructure(microstructure, dislocations)

    def _result_view_model(self, run: Run) -> ResultViewModel:
        notice, tone = "", Tone.NEUTRAL
        if isinstance(run, LineRun):
            results: tuple[TechniqueResult, ...] = (run.result,)
            size, strain = _microstructure_metrics("", run.result)
            notice, tone = _notice(results)
            solution = run.result.solutions[0] if run.result.solutions else None
        else:
            assert isinstance(run, MicrostructureRun)
            solution = run.solution
            m = solution.microstructure
            size = Metric("D, nm", size_text(m.size), "as entered")
            strain = Metric("es, %", strain_text(m.strain), "as entered")
        d = solution.densities if solution is not None else None
        hint = "switch on Dislocation density"
        density = (
            Metric(
                "Ldis, cm⁻²", power_text(d.williamson, 2), f"Williamson · {d.distribution}"
            )
            if d
            else Metric("Ldis, cm⁻²", EMPTY, hint)
        )
        ashby = (
            Metric("Ro_total, cm⁻²", power_text(d.ashby, 2), "Ashby")
            if d
            else Metric("Ro_total, cm⁻²", EMPTY, hint)
        )
        return ResultViewModel(
            (size, strain, density, ashby), notice, tone, self._service.report(run)
        )


class EstimatePresenter(_Exports):
    """The calculator: broadening from D, es - and D, es from widths or densities."""

    _view: EstimateView

    _NAMES: ClassVar = {
        Origin.MICROSTRUCTURE: ("D", "es"),
        Origin.WIDTHS: ("FWHM_size", "FWHM_strain"),
        Origin.DENSITIES: ("Ldis_D", "Ldis_es"),
    }

    def __init__(self, view: EstimateView, service: SizeStrainService) -> None:
        self._view = view
        self._service = service
        self._run: Run | None = None
        self._stem = "sizestrain_estimate"

    def calculate(self) -> None:
        try:
            inp = self._view.estimate_input()
            first_name, second_name = self._NAMES[inp.origin]
            h, k, l_ = (t.strip() for t in inp.hkl)
            hkl = (
                (parsing.integer(h, "h"), parsing.integer(k, "k"), parsing.integer(l_, "l"))
                if h and k and l_
                else None
            )
            request = EstimateRequest(
                origin=inp.origin,
                first=parsing.positive_pair(inp.first, first_name),
                second=parsing.positive_pair(inp.second, second_name),
                two_theta=parsing.required_pair(inp.two_theta, "2Theta"),
                hkl=hkl,
                instrument=parsing.instrument(self._view.instrument()),
                profile=self._view.instrument().profile,
                dislocations=(
                    parsing.dislocations(self._view.dislocations(), force=True)
                    if inp.origin is Origin.DENSITIES
                    else None
                ),
                rounded=inp.rounded,
            )
            run = self._service.estimate(request)
        except _PROBLEMS as error:
            self._run = None
            self._view.clear_result()
            self._view.show_error("Cannot estimate", str(error))
            return
        self._run = run
        e, b = run.estimate, run.estimate.broadening

        def width(caption: str, q: Quantity | None) -> Metric:
            if q is None:
                return Metric(caption, EMPTY, "not calculated")
            return Metric(caption, f"{q.value:.4f}", f"± {q.esd:.2g}°")

        def value(caption: str, q: Quantity | None, text: str) -> Metric:
            if q is None:
                return Metric(caption, EMPTY, "not estimated")
            if q.is_infinite:
                return Metric(caption, INFINITY, "no size broadening")
            if e.origin is Origin.MICROSTRUCTURE:
                return Metric(caption, text, "as set")
            return Metric(caption, text, esd_text(q, 5))

        metrics = (
            width("FWHM_size, °", b.size),
            width("FWHM_strain, °", b.strain),
            width("FWHM_corr, °", b.total),
            value("D, nm", e.size, size_text(e.size) if e.size is not None else ""),
            value("es, %", e.strain, strain_text(e.strain) if e.strain is not None else ""),
        )
        notice = (
            ""
            if b.total is not None
            else "From the densities each width comes from its own part alone: "
            "D for es = 0 and es for D = ∞, so there is no total."
        )
        self._view.show_result(
            ResultViewModel(metrics, notice, Tone.NEUTRAL, self._service.report(run))
        )
