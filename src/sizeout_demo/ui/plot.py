"""One WHP or SSP plot: the reflections, the fitted line and its equation.

A click on a point asks the presenter to use that reflection or leave it out.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QStackedLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, StrongBodyLabel

from sizeout_demo.ui.view import PlotViewModel

pg.setConfigOptions(antialias=True)


@dataclass(frozen=True, slots=True)
class PlotPalette:
    background: str
    text: str
    axis: str
    grid: int
    used: str
    unused: str
    line: str
    label: str


LIGHT = PlotPalette(
    background="#fbfbfb",
    text="#3b3b3b",
    axis="#b4b4b4",
    grid=40,
    used="#0067c0",
    unused="#9e9e9e",
    line="#d83b01",
    label="#555555",
)
DARK = PlotPalette(
    background="#2b2b2b",
    text="#d6d6d6",
    axis="#5a5a5a",
    grid=50,
    used="#4cc2ff",
    unused="#7a7a7a",
    line="#ff8c5a",
    label="#bdbdbd",
)


class LinePlot(QWidget):
    point_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model: PlotViewModel | None = None
        self._palette = LIGHT

        self.title = StrongBodyLabel("")
        self.equation = CaptionLabel("")
        self.equation.setFont(QFont("Consolas", 9))
        self._widget = pg.PlotWidget()
        self._plot = self._widget.getPlotItem()
        self._plot.setMenuEnabled(False)
        self._plot.hideButtons()
        for name in ("left", "bottom"):
            self._plot.getAxis(name).setStyle(tickFont=QFont("Segoe UI", 8))
        self._plot.getAxis("left").setWidth(58)
        self._plot.showGrid(x=True, y=True, alpha=0.15)

        self._placeholder = BodyLabel("Open reflections and press Calculate.")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QWidget()
        self._stack = QStackedLayout(body)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self._placeholder)
        self._stack.addWidget(self._widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 4)
        layout.setSpacing(2)
        layout.addWidget(self.title)
        layout.addWidget(self.equation)
        layout.addWidget(body, 1)
        self._apply_palette()

    def set_model(self, model: PlotViewModel) -> None:
        self._model = model
        self._draw()
        self._plot.enableAutoRange()
        self._stack.setCurrentWidget(self._widget)

    def clear(self) -> None:
        self._model = None
        self.title.setText("")
        self.equation.setText("")
        self._plot.clear()
        self._stack.setCurrentWidget(self._placeholder)

    def set_dark(self, dark: bool) -> None:
        self._palette = DARK if dark else LIGHT
        self._apply_palette()
        self._draw()

    # pyqtgraph resolves colours when an item is created, so a theme change
    # re-applies every pen and rebuilds the items.
    def _apply_palette(self) -> None:
        p = self._palette
        self._widget.setBackground(p.background)
        for name in ("left", "bottom"):
            axis = self._plot.getAxis(name)
            axis.setPen(p.axis)
            axis.setTextPen(p.text)

    def _draw(self) -> None:
        self._plot.clear()
        m, p = self._model, self._palette
        if m is None:
            return
        self.title.setText(m.title)
        self.equation.setText(m.equation)
        self._plot.setLabel("bottom", m.x_label, color=p.text)
        self._plot.setLabel("left", m.y_label, color=p.text)
        if m.line is not None:
            x0, y0, x1, y1 = m.line
            self._plot.plot([x0, x1], [y0, y1], pen=pg.mkPen(p.line, width=2))
        xs, ys = np.asarray(m.xs), np.asarray(m.ys)
        used = np.asarray(m.used, dtype=bool)
        brushes = [pg.mkBrush(p.used) if u else pg.mkBrush(0, 0, 0, 0) for u in m.used]
        pens = [pg.mkPen(p.used if u else p.unused, width=1.6) for u in m.used]
        scatter = pg.ScatterPlotItem(
            x=xs,
            y=ys,
            size=11,
            brush=brushes,
            pen=pens,
            data=list(range(len(xs))),
            hoverable=True,
            hoverSize=14,
            tip=None,
        )
        scatter.sigClicked.connect(self._clicked)
        self._plot.addItem(scatter)
        # neighbours in the list are neighbours on the plot: alternate the sides
        for i, (x, y, label, u) in enumerate(zip(xs, ys, m.labels, used, strict=True)):
            if label:
                anchor = (1.25, 0.9) if i % 2 else (-0.25, 0.1)
                text = pg.TextItem(label, color=p.label if u else p.unused, anchor=anchor)
                text.setFont(QFont("Segoe UI", 8))
                text.setPos(float(x), float(y))
                self._plot.addItem(text)

    def _clicked(self, _item: object, points: list[pg.SpotItem], _event: object) -> None:
        if points:
            self.point_clicked.emit(int(points[0].data()))
