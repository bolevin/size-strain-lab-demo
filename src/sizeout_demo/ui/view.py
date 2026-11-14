"""What the presenters may ask of the window, and the data they hand over.

The inputs arrive as the text the user typed; the presenters parse it.  The view
models carry text that is already formatted and plain tuples of numbers.  The
window draws them and decides nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from sizeout_demo.domain import Distribution, Origin, Profile, Technique

# ---- inputs, as typed ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PairInput:
    value: str = ""
    esd: str = ""


@dataclass(frozen=True, slots=True)
class InstrumentInput:
    wavelength: str
    k_size: str
    k_strain: str
    profile: Profile


@dataclass(frozen=True, slots=True)
class ReferenceInput:
    scherrer: PairInput
    monshi: PairInput
    stokes: PairInput


@dataclass(frozen=True, slots=True)
class DislocationInput:
    enabled: bool
    distribution: Distribution
    n: str
    k: str
    cubic: bool
    a: PairInput
    m: str
    uvw: tuple[str, str, str]
    b: PairInput
    rounded: bool


class LineMode(Enum):
    COEFFICIENTS = "Coefficients A, B"
    TWO_REFLECTIONS = "Two reflections"
    MICROSTRUCTURE = "D and es"


@dataclass(frozen=True, slots=True)
class LineInput:
    mode: LineMode
    technique: Technique
    intercept: PairInput
    slope: PairInput
    x1: PairInput
    y1: PairInput
    x2: PairInput
    y2: PairInput
    size: PairInput
    strain: PairInput


@dataclass(frozen=True, slots=True)
class EstimateInput:
    origin: Origin
    first: PairInput  # D, FWHM_size or Ldis_D
    second: PairInput  # es, FWHM_strain or Ldis_es
    two_theta: PairInput
    hkl: tuple[str, str, str]
    rounded: bool


# ---- view models -------------------------------------------------------------


class Tone(Enum):
    NEUTRAL = "neutral"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Metric:
    caption: str
    value: str
    hint: str = ""


@dataclass(frozen=True, slots=True)
class RowViewModel:
    hkl: str
    two_theta: str
    fwhm: str
    used: bool


@dataclass(frozen=True, slots=True)
class DataViewModel:
    file_name: str
    title: str
    summary: str
    rows: tuple[RowViewModel, ...]


@dataclass(frozen=True, slots=True)
class PlotViewModel:
    title: str
    x_label: str
    y_label: str
    xs: tuple[float, ...]
    ys: tuple[float, ...]
    used: tuple[bool, ...]
    labels: tuple[str, ...]
    line: tuple[float, float, float, float] | None  # x0, y0, x1, y1
    equation: str


@dataclass(frozen=True, slots=True)
class ResultViewModel:
    metrics: tuple[Metric, ...]
    notice: str
    tone: Tone
    report: str
    plots: tuple[PlotViewModel, ...] = ()


# ---- the window --------------------------------------------------------------


class Notifier(Protocol):
    def show_error(self, title: str, message: str) -> None: ...

    def show_success(self, title: str, message: str) -> None: ...

    def ask_save_path(self, suggested: Path, kind: str) -> Path | None: ...


class FitView(Notifier, Protocol):
    def show_data(self, data: DataViewModel) -> None: ...

    def show_result(self, result: ResultViewModel) -> None: ...

    def clear_result(self) -> None: ...

    def instrument(self) -> InstrumentInput: ...

    def references(self) -> ReferenceInput: ...

    def dislocations(self) -> DislocationInput: ...

    def ask_open_path(self) -> Path | None: ...


class LineView(Notifier, Protocol):
    def show_result(self, result: ResultViewModel) -> None: ...

    def clear_result(self) -> None: ...

    def line_input(self) -> LineInput: ...

    def instrument(self) -> InstrumentInput: ...

    def references(self) -> ReferenceInput: ...

    def dislocations(self) -> DislocationInput: ...


class EstimateView(Notifier, Protocol):
    def show_result(self, result: ResultViewModel) -> None: ...

    def clear_result(self) -> None: ...

    def estimate_input(self) -> EstimateInput: ...

    def instrument(self) -> InstrumentInput: ...

    def dislocations(self) -> DislocationInput: ...
