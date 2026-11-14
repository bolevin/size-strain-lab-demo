"""Every user intent, through the presenters, against a fake window - no Qt."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pytest

from sizeout_demo.application import SizeStrainService
from sizeout_demo.domain import Distribution, Origin, Profile, Technique
from sizeout_demo.ui.presenters import EstimatePresenter, FitPresenter, LinePresenter
from sizeout_demo.ui.view import (
    DataViewModel,
    DislocationInput,
    EstimateInput,
    InstrumentInput,
    LineInput,
    LineMode,
    PairInput,
    ReferenceInput,
    ResultViewModel,
    Tone,
)

NO_REFERENCES = ReferenceInput(PairInput(), PairInput(), PairInput())


@dataclass
class FakeView:
    """Records what the presenter shows; answers what the test sets."""

    instrument_input: InstrumentInput = field(
        default_factory=lambda: InstrumentInput(
            "1.540598", "0.94", "4", Profile.PSEUDO_VOIGT
        )
    )
    reference_input: ReferenceInput = NO_REFERENCES
    dislocation_input: DislocationInput = field(
        default_factory=lambda: DislocationInput(
            enabled=False,
            distribution=Distribution.ANISOTROPIC,
            n="1",
            k="12",
            cubic=True,
            a=PairInput("4.0495", ""),
            m="2",
            uvw=("1", "-1", "0"),
            b=PairInput("0.2863", ""),
            rounded=True,
        )
    )
    line: LineInput | None = None
    estimate: EstimateInput | None = None
    open_path: Path | None = None
    save_path: Path | None = None
    data: list[DataViewModel] = field(default_factory=list)
    results: list[ResultViewModel] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)
    successes: list[str] = field(default_factory=list)
    cleared: int = 0
    asked: list[tuple[Path, str]] = field(default_factory=list)

    def show_data(self, data: DataViewModel) -> None:
        self.data.append(data)

    def show_result(self, result: ResultViewModel) -> None:
        self.results.append(result)

    def clear_result(self) -> None:
        self.cleared += 1

    def show_error(self, title: str, message: str) -> None:
        self.errors.append((title, message))

    def show_success(self, title: str, message: str) -> None:
        self.successes.append(title)

    def instrument(self) -> InstrumentInput:
        return self.instrument_input

    def references(self) -> ReferenceInput:
        return self.reference_input

    def dislocations(self) -> DislocationInput:
        return self.dislocation_input

    def line_input(self) -> LineInput:
        assert self.line is not None
        return self.line

    def estimate_input(self) -> EstimateInput:
        assert self.estimate is not None
        return self.estimate

    def ask_open_path(self) -> Path | None:
        return self.open_path

    def ask_save_path(self, suggested: Path, kind: str) -> Path | None:
        self.asked.append((suggested, kind))
        return self.save_path


@pytest.fixture
def view() -> FakeView:
    return FakeView()


@pytest.fixture
def fit(view: FakeView, service: SizeStrainService, sample_path: Path) -> FitPresenter:
    return FitPresenter(view, service, sample_path)


# ---- fit ---------------------------------------------------------------------


def test_calculate_before_loading_is_refused(view: FakeView, fit: FitPresenter) -> None:
    fit.calculate()
    assert view.errors == [("No reflections", "Open a reflection list first.")]


def test_sample_fit_with_densities(view: FakeView, fit: FitPresenter) -> None:
    fit.open_sample()
    assert view.data[-1].summary == "9 reflections, 8 used, 2θ 38.5 - 137.5°"
    assert [r.used for r in view.data[-1].rows].count(False) == 1
    view.dislocation_input = replace(view.dislocation_input, enabled=True)
    fit.calculate()
    result = view.results[-1]
    assert [m.value for m in result.metrics[:4]] == [
        "43 ± 1",
        "0.117 ± 0.003",
        "42.9 ± 0.6",
        "0.116 ± 0.002",
    ]
    assert result.metrics[0].hint == "R² = 0.9853"
    assert result.metrics[4].caption.startswith("WHP · Ldis")
    assert result.metrics[4].value == "(5.7 ± 0.2)·10¹⁰"
    assert [p.title for p in result.plots] == [
        "Williamson-Hall plot · pseudo-Voigt",
        "Size-strain plot · pseudo-Voigt",
    ]
    whp = result.plots[0]
    assert len(whp.xs) == 9
    assert whp.used.count(False) == 1
    assert whp.line is not None
    assert whp.line[0] == 0.0  # drawn from x = 0: the intercept shows
    assert result.notice == ""


def test_without_densities_the_last_card_counts_reflections(
    view: FakeView, fit: FitPresenter
) -> None:
    fit.open_sample()
    fit.calculate()
    assert view.results[-1].metrics[4].value == "8 of 9"


def test_toggling_a_point_refits(view: FakeView, fit: FitPresenter) -> None:
    fit.open_sample()
    fit.calculate()
    before = view.results[-1].metrics[0].value
    fit.toggle(6)  # put 331 back into the fit
    assert view.data[-1].rows[6].used
    assert len(view.results) == 2
    assert view.results[-1].metrics[0].value != before
    fit.toggle(99)  # out of range: ignored
    assert len(view.results) == 2


def test_toggle_before_calculating_does_not_calculate(
    view: FakeView, fit: FitPresenter
) -> None:
    fit.open_sample()
    fit.toggle(0)
    assert view.results == []
    assert not view.data[-1].rows[0].used


def test_bad_input_clears_and_explains(view: FakeView, fit: FitPresenter) -> None:
    fit.open_sample()
    view.instrument_input = replace(view.instrument_input, wavelength="1,5x")
    fit.calculate()
    assert view.errors == [("Cannot calculate", "Wavelength: '1,5x' is not a number")]
    assert view.cleared == 2  # once on load, once on the error


def test_a_missing_model_is_a_warning_not_an_error(
    view: FakeView, fit: FitPresenter, tmp_path: Path
) -> None:
    # widths that fall with angle: the WHP line slopes down - no strain
    path = tmp_path / "flat.csv"
    path.write_text(
        "two_theta,fwhm\n30,0.40\n60,0.36\n90,0.38\n120,0.41\n", encoding="utf-8"
    )
    fit.load(path)
    fit.calculate()
    result = view.results[-1]
    assert result.tone is Tone.WARNING
    assert "D0 of Scherrer" in result.notice
    assert result.metrics[0].value == "—"


def test_open_file_errors_are_shown(
    view: FakeView, fit: FitPresenter, tmp_path: Path
) -> None:
    view.open_path = tmp_path / "missing.csv"
    fit.open_file()
    assert view.errors[0][0] == "Cannot open missing.csv"
    view.open_path = None
    fit.open_file()  # cancelled: nothing happens
    assert len(view.errors) == 1


def test_save_report_and_table(view: FakeView, fit: FitPresenter, tmp_path: Path) -> None:
    fit.save_report()
    assert view.errors == [("Nothing to save", "Run the calculation first.")]
    fit.open_sample()
    fit.calculate()
    view.save_path = tmp_path / "out.txt"
    fit.save_report()
    assert view.asked[-1][0].name == "sample_reflections_sizestrain.txt"
    assert "Williamson-Hall plot" in view.save_path.read_text("utf-8")
    view.save_path = tmp_path / "out.csv"
    fit.export_table()
    assert view.save_path.read_text("utf-8").startswith("calculation,technique")
    assert view.successes == ["Report saved", "Table saved"]
    view.save_path = tmp_path / "no-such-folder" / "x.txt"
    fit.save_report()
    assert view.errors[-1][0] == "Cannot save the report"


# ---- from a line ---------------------------------------------------------------


def line_input(mode: LineMode, **changes: Any) -> LineInput:
    base = LineInput(
        mode,
        Technique.WHP,
        PairInput("3.3458e-3", "9.7e-5"),
        PairInput("1.37055e-6", "6.8e-8"),
        PairInput("1e-4", "4e-6"),
        PairInput("3.52e-3", "8e-5"),
        PairInput("9.6e-4", "1.2e-5"),
        PairInput("4.67e-3", "9e-5"),
        PairInput("45", "2"),
        PairInput("0.12", "0.01"),
    )
    return replace(base, **changes)


def test_line_coefficients(view: FakeView, service: SizeStrainService) -> None:
    presenter = LinePresenter(view, service)
    view.line = line_input(LineMode.COEFFICIENTS)
    presenter.calculate()
    metrics = view.results[-1].metrics
    assert [m.value for m in metrics[:2]] == ["43 ± 1", "0.117 ± 0.003"]
    assert metrics[2].hint == "switch on Dislocation density"


def test_two_reflections(view: FakeView, service: SizeStrainService) -> None:
    presenter = LinePresenter(view, service)
    view.line = line_input(LineMode.TWO_REFLECTIONS)
    presenter.calculate()
    assert "two reflections" in view.results[-1].report


def test_microstructure_forces_the_densities(
    view: FakeView, service: SizeStrainService
) -> None:
    presenter = LinePresenter(view, service)
    view.line = line_input(LineMode.MICROSTRUCTURE)
    presenter.calculate()
    metrics = view.results[-1].metrics
    assert metrics[0].hint == "as entered"
    assert metrics[2].value == "(5.6 ± 0.5)·10¹⁰"
    assert metrics[3].hint == "Ashby"


def test_microstructure_zero_size_is_infinite(
    view: FakeView, service: SizeStrainService
) -> None:
    presenter = LinePresenter(view, service)
    view.line = line_input(LineMode.MICROSTRUCTURE, size=PairInput("0", ""))
    presenter.calculate()
    assert view.results[-1].metrics[0].value == "∞"


def test_line_errors(view: FakeView, service: SizeStrainService) -> None:
    presenter = LinePresenter(view, service)
    view.line = line_input(LineMode.COEFFICIENTS, slope=PairInput("", ""))
    presenter.calculate()
    assert view.errors == [("Cannot calculate", "B is empty")]


# ---- the calculator ----------------------------------------------------------------


def estimate_input(origin: Origin, first: PairInput, second: PairInput) -> EstimateInput:
    return EstimateInput(
        origin, first, second, PairInput("38.4735", "0.01"), ("1", "1", "1"), rounded=False
    )


def test_estimate_from_size_and_strain(view: FakeView, service: SizeStrainService) -> None:
    presenter = EstimatePresenter(view, service)
    view.estimate = estimate_input(
        Origin.MICROSTRUCTURE, PairInput("45", "2"), PairInput("0.12", "0.01")
    )
    presenter.calculate()
    metrics = view.results[-1].metrics
    assert [m.value for m in metrics] == [
        "0.1953",
        "0.0960",
        "0.2346",
        "45 ± 2",
        "0.12 ± 0.01",
    ]
    assert "Dislocations" not in view.results[-1].report


def test_estimate_from_densities_has_no_total(
    view: FakeView, service: SizeStrainService
) -> None:
    presenter = EstimatePresenter(view, service)
    view.estimate = estimate_input(
        Origin.DENSITIES, PairInput("1.5e11", "1e10"), PairInput("2e10", "1e9")
    )
    presenter.calculate()
    result = view.results[-1]
    assert result.metrics[2].value == "—"
    assert "no total" in result.notice
    assert "Dislocations" in result.report


def test_estimate_errors(view: FakeView, service: SizeStrainService) -> None:
    presenter = EstimatePresenter(view, service)
    view.estimate = estimate_input(Origin.WIDTHS, PairInput(), PairInput())
    presenter.calculate()
    assert view.errors == [("Cannot estimate", "set FWHM_size and / or FWHM_strain")]
    view.estimate = replace(
        estimate_input(Origin.WIDTHS, PairInput("0.2"), PairInput()), hkl=("1", "x", "1")
    )
    presenter.calculate()
    assert view.errors[-1] == ("Cannot estimate", "k: 'x' is not a number")
