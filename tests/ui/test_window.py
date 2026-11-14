"""The real window, driven through its widgets."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot
from qfluentwidgets import Theme, isDarkTheme, setTheme

from sizeout_demo.domain import Origin
from sizeout_demo.main import build_service
from sizeout_demo.ui.main_window import MainWindow
from sizeout_demo.ui.plot import DARK, LIGHT
from sizeout_demo.ui.presenters import EstimatePresenter, FitPresenter, LinePresenter
from sizeout_demo.ui.view import LineMode


@pytest.fixture
def window(qtbot: QtBot, sample_path: Path) -> MainWindow:
    setTheme(Theme.LIGHT)
    window = MainWindow()
    qtbot.addWidget(window)
    service = build_service()
    presenters = (
        FitPresenter(window.fit, service, sample_path),
        LinePresenter(window.line, service),
        EstimatePresenter(window.estimate, service),
    )
    window.fit.bind(presenters[0])
    window.line.bind(presenters[1])
    window.estimate.bind(presenters[2])
    window.presenters = presenters
    return window


def click(qtbot: QtBot, button: QWidget) -> None:
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)  # type: ignore[no-untyped-call]


def test_nothing_can_be_calculated_before_reflections_are_loaded(
    window: MainWindow,
) -> None:
    page = window.fit
    assert not page.calculate_button.isEnabled()
    assert not page.save_button.isEnabled()
    assert page.notice.isHidden()


def test_load_calculate_and_read_the_cards(qtbot: QtBot, window: MainWindow) -> None:
    page = window.fit
    click(qtbot, page.sample_button)
    assert page.file_label.text() == "sample_reflections.csv"
    assert page.table.rowCount() == 9
    assert page.table.item(6, 0).checkState() == Qt.CheckState.Unchecked
    page.dislocation_card.switch.setChecked(True)
    click(qtbot, page.calculate_button)
    assert [c.value.text() for c in page.metric_cards[:4]] == [
        "43 ± 1",
        "0.117 ± 0.003",
        "42.9 ± 0.6",
        "0.116 ± 0.002",
    ]
    assert page.metric_cards[4].caption.text().startswith("WHP · Ldis")
    assert page.plots[0].title.text() == "Williamson-Hall plot · pseudo-Voigt"
    assert page.plots[0].equation.text().startswith("y = 0.003346 + 1.371e-06·x")
    assert "Ro_total" in page.report.toPlainText()
    assert page.save_button.isEnabled()
    assert page.table_button.isEnabled()


def test_the_table_checkbox_refits(qtbot: QtBot, window: MainWindow) -> None:
    page = window.fit
    click(qtbot, page.sample_button)
    click(qtbot, page.calculate_button)
    before = page.metric_cards[0].value.text()
    page.table.item(6, 0).setCheckState(Qt.CheckState.Checked)
    assert page.metric_cards[0].value.text() != before
    assert page.table.item(6, 0).checkState() == Qt.CheckState.Checked


def test_a_click_on_a_point_refits(qtbot: QtBot, window: MainWindow) -> None:
    page = window.fit
    click(qtbot, page.sample_button)
    click(qtbot, page.calculate_button)
    page.plots[1].point_clicked.emit(0)  # what a click on 111 sends
    assert page.table.item(0, 0).checkState() == Qt.CheckState.Unchecked
    assert "Reflections (9, 7 used)" in page.report.toPlainText()


def test_profile_change_relabels_the_plots(qtbot: QtBot, window: MainWindow) -> None:
    page = window.fit
    click(qtbot, page.sample_button)
    page.instrument_card.profile.setCurrentIndex(1)  # Gauss
    click(qtbot, page.calculate_button)
    assert page.plots[0].title.text().endswith("Gauss")
    assert page.metric_cards[0].value.text() == "41 ± 1"


def test_line_page_modes(qtbot: QtBot, window: MainWindow) -> None:
    page = window.line
    click(qtbot, page.calculate_button)
    assert page.metric_cards[0].value.text() == "43 ± 1"
    page.mode.setCurrentIndex(list(LineMode).index(LineMode.MICROSTRUCTURE))
    assert page.size_row.value.isVisibleTo(page)
    assert not page.intercept.value.isVisibleTo(page)  # one form at a time
    assert page.dislocation_card.switch.isChecked()
    assert not page.reference_card.isEnabled()
    click(qtbot, page.calculate_button)
    assert page.metric_cards[3].value.text() == "(1.7 ± 0.1)·10¹¹"


def test_estimate_page_groups(qtbot: QtBot, window: MainWindow) -> None:
    page = window.estimate
    assert page.dislocation_card.isHidden()
    click(qtbot, page.calculate_button)
    assert page.metric_cards[2].value.text() == "0.2346"
    page.origin.setCurrentIndex(list(Origin).index(Origin.DENSITIES))
    assert not page.dislocation_card.isHidden()
    click(qtbot, page.calculate_button)
    assert page.metric_cards[2].value.text() == "—"
    assert not page.notice.isHidden()


def test_theme_switch_recolours_the_plots(window: MainWindow) -> None:
    window.set_dark(True)
    assert isDarkTheme()
    assert window.fit.plots[0]._palette is DARK
    window.toggle_theme()
    assert not isDarkTheme()
    assert window.fit.plots[0]._palette is LIGHT
