"""The pages of the window.  Each is a passive view of its own presenter."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import ClassVar, Protocol

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QStackedWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    CheckBox,
    ComboBox,
    InfoBar,
    InfoBarPosition,
    PlainTextEdit,
    PrimaryPushButton,
    PushButton,
    SegmentedWidget,
    SmoothScrollArea,
    TableWidget,
)
from qfluentwidgets import FluentIcon as Icon

from sizeout_demo.domain import Origin, Technique
from sizeout_demo.ui.plot import LinePlot
from sizeout_demo.ui.view import (
    DataViewModel,
    DislocationInput,
    EstimateInput,
    InstrumentInput,
    LineInput,
    LineMode,
    ReferenceInput,
    ResultViewModel,
)
from sizeout_demo.ui.widgets import (
    DislocationCard,
    InstrumentCard,
    MetricCard,
    NoticeBar,
    NumberEdit,
    PairRow,
    ReferenceCard,
    caption,
    pair_grid,
    titled_card,
)

LEFT_WIDTH = 372


class Calculating(Protocol):
    def calculate(self) -> None: ...

    def save_report(self) -> None: ...

    def export_table(self) -> None: ...


def report_box() -> PlainTextEdit:
    box = PlainTextEdit()
    box.setReadOnly(True)
    box.setFont(QFont("Consolas", 10))
    box.setLineWrapMode(PlainTextEdit.LineWrapMode.NoWrap)
    box.setPlaceholderText("The report appears here after the calculation.")
    return box


class _Page(QWidget):
    """Inputs on the left in a scrolled column, results on the right."""

    def __init__(self, name: str, metrics: Sequence[str]) -> None:
        super().__init__()
        self.setObjectName(name)
        self.inputs = QVBoxLayout()
        self.inputs.setContentsMargins(0, 0, 10, 0)
        self.inputs.setSpacing(12)
        holder = QWidget()
        holder.setObjectName(f"{name}Inputs")
        holder.setLayout(self.inputs)
        holder.setStyleSheet(f"#{name}Inputs{{background:transparent}}")
        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidget(holder)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea{border:none;background:transparent}")

        self.calculate_button = PrimaryPushButton(Icon.PLAY, "Calculate")
        self.save_button = PushButton(Icon.SAVE, "Report")
        self.table_button = PushButton(Icon.DOWNLOAD, "CSV")
        self.save_button.setToolTip("Save the report as text")
        self.table_button.setToolTip("Export the results as a CSV table")
        for button in (self.save_button, self.table_button):
            button.setEnabled(False)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.calculate_button, 2)
        buttons.addWidget(self.save_button, 1)
        buttons.addWidget(self.table_button, 1)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(12)
        left.addWidget(self.scroll_area, 1)
        left.addLayout(buttons)
        left_holder = QWidget()
        left_holder.setLayout(left)
        left_holder.setFixedWidth(LEFT_WIDTH)

        self.metric_cards = [MetricCard(text) for text in metrics]
        row = QHBoxLayout()
        row.setSpacing(10)
        for card in self.metric_cards:
            row.addWidget(card, 1)
        self.notice = NoticeBar()
        self.results = QVBoxLayout()
        self.results.setSpacing(12)
        self.results.addLayout(row)
        self.results.addWidget(self.notice)

        page = QHBoxLayout(self)
        page.setContentsMargins(24, 16, 24, 20)
        page.setSpacing(20)
        page.addWidget(left_holder)
        page.addLayout(self.results, 1)

    def bind_calculation(self, actions: Calculating) -> None:
        self.calculate_button.clicked.connect(actions.calculate)
        self.save_button.clicked.connect(actions.save_report)
        self.table_button.clicked.connect(actions.export_table)

    # ---- the parts of the view every page shares -----------------------
    def _show_common(self, result: ResultViewModel) -> None:
        for card, metric in zip(self.metric_cards, result.metrics, strict=True):
            card.show_metric(metric)
        self.notice.show_notice(result.notice, result.tone)
        for button in (self.save_button, self.table_button):
            button.setEnabled(True)

    def _clear_common(self) -> None:
        for card in self.metric_cards:
            card.show_metric(None)
        self.notice.hide()
        for button in (self.save_button, self.table_button):
            button.setEnabled(False)

    def show_error(self, title: str, message: str) -> None:
        InfoBar.error(
            title,
            message,
            duration=8000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self.window(),
        )

    def show_success(self, title: str, message: str) -> None:
        InfoBar.success(
            title,
            message,
            duration=5000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self.window(),
        )

    def ask_save_path(self, suggested: Path, kind: str) -> Path | None:
        pattern = "Text file (*.txt)" if kind == "report" else "CSV table (*.csv)"
        name, _ = QFileDialog.getSaveFileName(
            self, f"Save the {kind}", str(suggested), f"{pattern};;All files (*)"
        )
        return Path(name) if name else None


def _tabs(stack: QStackedWidget, items: Sequence[tuple[str, str]]) -> SegmentedWidget:
    tabs = SegmentedWidget()
    for index, (key, text) in enumerate(items):
        tabs.addItem(key, text, lambda i=index: stack.setCurrentIndex(i))
    tabs.setCurrentItem(items[0][0])
    return tabs


class FitPage(_Page):
    """Reflections -> Williamson-Hall and size-strain plots side by side."""

    def __init__(self) -> None:
        super().__init__(
            "fitPage",
            (
                "WHP · D, nm",
                "WHP · es, %",
                "SSP · D, nm",
                "SSP · es, %",
                "Reflections used",
            ),
        )
        data_card, data = titled_card("Reflections")
        self.file_label = BodyLabel("No file loaded")
        self.title_label = caption("")
        self.summary_label = caption("")
        self.open_button = PushButton(Icon.FOLDER, "Open CSV")
        self.sample_button = PushButton(Icon.DOCUMENT, "Load sample")
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.sample_button)
        for widget in (self.file_label, self.title_label, self.summary_label):
            data.addWidget(widget)
        data.addLayout(buttons)
        self.instrument_card = InstrumentCard()
        self.dislocation_card = DislocationCard()
        self.reference_card = ReferenceCard()
        for card in (
            data_card,
            self.instrument_card,
            self.dislocation_card,
            self.reference_card,
        ):
            self.inputs.addWidget(card)
        self.inputs.addStretch(1)

        self.plots = (LinePlot(), LinePlot())
        plots = QWidget()
        plot_row = QHBoxLayout(plots)
        plot_row.setContentsMargins(0, 0, 0, 0)
        plot_row.setSpacing(12)
        for plot in self.plots:
            card = CardWidget()
            inner = QVBoxLayout(card)
            inner.setContentsMargins(4, 6, 4, 4)
            inner.addWidget(plot)
            plot_row.addWidget(card, 1)
        self.table = TableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Use", "hkl", "2θ, °", "FWHM, °"])
        self.table.verticalHeader().hide()
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.report = report_box()
        self.stack = QStackedWidget()
        for widget in (plots, self.table, self.report):
            self.stack.addWidget(widget)
        self.tabs = _tabs(
            self.stack, (("plots", "Plots"), ("table", "Reflections"), ("report", "Report"))
        )
        tabs_row = QHBoxLayout()
        tabs_row.addWidget(self.tabs)
        tabs_row.addStretch(1)
        self.results.addLayout(tabs_row)
        self.results.addWidget(self.stack, 1)
        self.calculate_button.setEnabled(False)
        self._toggle: Callable[[int], None] | None = None
        self.table.itemChanged.connect(self._item_changed)

    def bind(self, actions: FitActions) -> None:
        self.bind_calculation(actions)
        self.open_button.clicked.connect(actions.open_file)
        self.sample_button.clicked.connect(actions.open_sample)
        self._toggle = actions.toggle
        for plot in self.plots:
            plot.point_clicked.connect(actions.toggle)

    def _item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0 and self._toggle is not None:
            self._toggle(item.row())

    # ---- FitView ---------------------------------------------------------
    def show_data(self, data: DataViewModel) -> None:
        self.file_label.setText(data.file_name)
        self.title_label.setText(data.title)
        self.summary_label.setText(data.summary)
        self.table.blockSignals(True)
        self.table.setRowCount(len(data.rows))
        for row, r in enumerate(data.rows):
            use = QTableWidgetItem("")
            use.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            use.setCheckState(Qt.CheckState.Checked if r.used else Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, use)
            for column, text in enumerate((r.hkl, r.two_theta, r.fwhm), start=1):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                alignment = (
                    Qt.AlignmentFlag.AlignRight
                    if column > 1
                    else Qt.AlignmentFlag.AlignLeft
                )
                item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
        self.table.setColumnWidth(0, 64)
        self.table.blockSignals(False)
        self.calculate_button.setEnabled(True)

    def show_result(self, result: ResultViewModel) -> None:
        self._show_common(result)
        for plot, model in zip(self.plots, result.plots, strict=True):
            plot.set_model(model)
        self.report.setPlainText(result.report)

    def clear_result(self) -> None:
        self._clear_common()
        for plot in self.plots:
            plot.clear()
        self.report.clear()

    def instrument(self) -> InstrumentInput:
        return self.instrument_card.input()

    def references(self) -> ReferenceInput:
        return self.reference_card.input()

    def dislocations(self) -> DislocationInput:
        return self.dislocation_card.input()

    def ask_open_path(self) -> Path | None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Open reflections", "", "Reflection list (*.csv *.txt);;All files (*)"
        )
        return Path(name) if name else None

    def set_dark(self, dark: bool) -> None:
        for plot in self.plots:
            plot.set_dark(dark)
        self.notice.update()


class FitActions(Calculating, Protocol):
    def open_file(self) -> None: ...

    def open_sample(self) -> None: ...

    def toggle(self, index: int) -> None: ...


class FormSwitch(QWidget):
    """Several forms in one place, one visible at a time.

    Unlike a QStackedWidget it is as tall as the visible form, not as the tallest one:
    hidden widgets take no room in a box layout.
    """

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._forms: list[QWidget] = []

    def add(self, form: QWidget) -> None:
        self._forms.append(form)
        self._layout.addWidget(form)
        form.setVisible(len(self._forms) == 1)

    def show_only(self, index: int) -> None:
        for i, form in enumerate(self._forms):
            form.setVisible(i == index)


def _mode_combo(items: Sequence[tuple[str, object]]) -> ComboBox:
    combo = ComboBox()
    for text, data in items:
        combo.addItem(text, userData=data)
    return combo


class LinePage(_Page):
    """A line typed in, a line through two reflections, or D and es typed in."""

    def __init__(self) -> None:
        super().__init__("linePage", ("D, nm", "es, %", "Ldis, cm⁻²", "Ro_total, cm⁻²"))
        card, box = titled_card("What is known")
        self.mode = _mode_combo([(m.value, m) for m in LineMode])
        self.technique = _mode_combo([(t.value, t) for t in Technique])
        grid = pair_grid()
        grid.addWidget(BodyLabel("Input"), 0, 0)
        grid.addWidget(self.mode, 0, 1, 1, 4)
        grid.addWidget(BodyLabel("Technique"), 1, 0)
        grid.addWidget(self.technique, 1, 1, 1, 4)
        box.addLayout(grid)

        self.forms = FormSwitch()
        coefficients, c = self._form()
        self.intercept = PairRow(
            c, 0, "A (intercept)", unit="", value="3.3458e-3", esd="9.7e-5"
        )
        self.slope = PairRow(c, 1, "B (slope)", unit="", value="1.37055e-6", esd="6.8e-8")
        two, t = self._form()
        self.x1 = PairRow(t, 0, "x1", unit="", value="0.000120", esd="0.000004")
        self.y1 = PairRow(t, 1, "y1", unit="", value="0.003520", esd="0.00008")
        self.x2 = PairRow(t, 2, "x2", unit="", value="0.000960", esd="0.000012")
        self.y2 = PairRow(t, 3, "y2", unit="", value="0.004670", esd="0.00009")
        micro, m = self._form()
        self.size_row = PairRow(m, 0, "D", unit="nm", value="45", esd="2")
        self.strain_row = PairRow(m, 1, "es", unit="%", value="0.12", esd="0.01")
        m.addWidget(caption("D = 0 is the infinite crystallite."), 2, 0, 1, 5)
        for form in (coefficients, two, micro):
            self.forms.add(form)
        box.addWidget(self.forms)
        self.instrument_card = InstrumentCard()
        self.dislocation_card = DislocationCard()
        self.reference_card = ReferenceCard()
        for widget in (
            card,
            self.instrument_card,
            self.dislocation_card,
            self.reference_card,
        ):
            self.inputs.addWidget(widget)
        self.inputs.addStretch(1)
        self.report = report_box()
        self.results.addWidget(self.report, 1)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self._mode_changed()

    @staticmethod
    def _form() -> tuple[QWidget, QGridLayout]:
        form = QWidget()
        grid = pair_grid()
        grid.setContentsMargins(0, 0, 0, 0)
        form.setLayout(grid)
        return form, grid

    def _mode_changed(self) -> None:
        mode: LineMode = self.mode.currentData()
        self.forms.show_only(list(LineMode).index(mode))
        micro = mode is LineMode.MICROSTRUCTURE
        self.technique.setEnabled(not micro)
        self.reference_card.setEnabled(not micro)
        if micro:
            self.dislocation_card.switch.setChecked(True)

    def bind(self, actions: Calculating) -> None:
        self.bind_calculation(actions)

    def line_input(self) -> LineInput:
        return LineInput(
            mode=self.mode.currentData(),
            technique=self.technique.currentData(),
            intercept=self.intercept.input(),
            slope=self.slope.input(),
            x1=self.x1.input(),
            y1=self.y1.input(),
            x2=self.x2.input(),
            y2=self.y2.input(),
            size=self.size_row.input(),
            strain=self.strain_row.input(),
        )

    def show_result(self, result: ResultViewModel) -> None:
        self._show_common(result)
        self.report.setPlainText(result.report)

    def clear_result(self) -> None:
        self._clear_common()
        self.report.clear()

    def instrument(self) -> InstrumentInput:
        return self.instrument_card.input()

    def references(self) -> ReferenceInput:
        return self.reference_card.input()

    def dislocations(self) -> DislocationInput:
        return self.dislocation_card.input()


class EstimatePage(_Page):
    """The calculator: widths from D and es, D and es from widths or densities."""

    _ROWS: ClassVar = {
        Origin.MICROSTRUCTURE: (("D", "nm", "45", "2"), ("es", "%", "0.12", "0.01")),
        Origin.WIDTHS: (
            ("FWHM_size", "°", "0.18", "0.01"),
            ("FWHM_strain", "°", "0.06", "0.005"),
        ),
        Origin.DENSITIES: (
            ("Ldis_D", "cm⁻²", "1.5e11", "1e10"),
            ("Ldis_es", "cm⁻²", "2.0e10", "1e9"),
        ),
    }

    def __init__(self) -> None:
        super().__init__(
            "estimatePage",
            ("FWHM_size, °", "FWHM_strain, °", "FWHM_corr, °", "D, nm", "es, %"),
        )
        card, box = titled_card("Estimate from")
        self.origin = _mode_combo([(o.value, o) for o in Origin])
        box.addWidget(self.origin)
        self.forms = FormSwitch()
        self.pairs: dict[Origin, tuple[PairRow, PairRow]] = {}
        for origin, rows in self._ROWS.items():
            form, grid = LinePage._form()
            first, second = (
                PairRow(grid, i, text, unit=unit, value=value, esd=esd)
                for i, (text, unit, value, esd) in enumerate(rows)
            )
            self.pairs[origin] = (first, second)
            self.forms.add(form)
        box.addWidget(self.forms)
        box.addWidget(
            caption("One group at a time; an empty value is absent (es = 0 or D = ∞).")
        )
        reflection_card, reflection = titled_card("Reflection")
        grid = pair_grid()
        self.two_theta = PairRow(grid, 0, "2θ", unit="°", value="38.4735", esd="0.01")
        self.h, self.k, self.l = (NumberEdit(t, width=44) for t in ("1", "1", "1"))
        indices = QHBoxLayout()
        indices.setSpacing(6)
        indices.addWidget(BodyLabel("h k l"))
        indices.addStretch(1)
        for edit in (self.h, self.k, self.l):
            indices.addWidget(edit)
        grid.addLayout(indices, 1, 0, 1, 5)
        reflection.addLayout(grid)
        self.rounded = CheckBox("Round D, es and b as published")
        reflection.addWidget(self.rounded)
        self.instrument_card = InstrumentCard()
        self.dislocation_card = DislocationCard(
            switchable=False, title="Dislocation parameters"
        )
        for widget in (card, reflection_card, self.instrument_card, self.dislocation_card):
            self.inputs.addWidget(widget)
        self.inputs.addStretch(1)
        self.report = report_box()
        self.results.addWidget(self.report, 1)
        self.origin.currentIndexChanged.connect(self._origin_changed)
        self._origin_changed()

    def _origin_changed(self) -> None:
        origin: Origin = self.origin.currentData()
        self.forms.show_only(list(Origin).index(origin))
        self.dislocation_card.setVisible(origin is Origin.DENSITIES)

    def bind(self, actions: Calculating) -> None:
        self.bind_calculation(actions)

    def estimate_input(self) -> EstimateInput:
        origin: Origin = self.origin.currentData()
        first, second = self.pairs[origin]
        return EstimateInput(
            origin,
            first.input(),
            second.input(),
            self.two_theta.input(),
            (self.h.text(), self.k.text(), self.l.text()),
            self.rounded.isChecked(),
        )

    def show_result(self, result: ResultViewModel) -> None:
        self._show_common(result)
        self.report.setPlainText(result.report)

    def clear_result(self) -> None:
        self._clear_common()
        self.report.clear()

    def instrument(self) -> InstrumentInput:
        return self.instrument_card.input()

    def dislocations(self) -> DislocationInput:
        return self.dislocation_card.input()
