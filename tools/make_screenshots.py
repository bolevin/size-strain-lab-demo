"""Render the screenshots used in the README.

    python tools/make_screenshots.py [output folder]

The window is laid out by the real Windows platform plugin but never appears on
screen; it is rendered at 2x into ``docs/img``.  Every picture shows the bundled
synthetic sample or the default values of the fields, so the result is
reproducible.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme, setThemeColor

from sizeout_demo.main import build_service, data_path
from sizeout_demo.ui.main_window import MainWindow
from sizeout_demo.ui.presenters import EstimatePresenter, FitPresenter, LinePresenter
from sizeout_demo.ui.view import LineMode

OUT = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(__file__).resolve().parents[1] / "docs" / "img"
)
SCALE = 2
SIZE = (1360, 860)
PAGE = {False: "#f3f3f3", True: "#202020"}  # window background per theme
BACKDROP = {False: ("#d3e9ee", "#8cc4d2"), True: ("#13303a", "#081419")}


def settle(app: QApplication, seconds: float = 0.2) -> None:
    """Let layouts and animations finish; a theme switch fades for a while."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def grab(window: MainWindow, dark: bool) -> Image.Image:
    pixmap = QPixmap(window.size() * SCALE)
    pixmap.setDevicePixelRatio(SCALE)
    pixmap.fill(QColor(PAGE[dark]))
    window.render(pixmap, QPoint(0, 0))
    raw = OUT / "_raw.png"
    pixmap.save(str(raw))
    image = Image.open(raw).convert("RGBA")
    image.load()
    raw.unlink()
    return image


def framed(shot: Image.Image, top: str, bottom: str, margin: int = 110) -> Image.Image:
    """The window on a gradient backdrop with rounded corners and a soft shadow."""
    radius = 9 * SCALE
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, *shot.size], radius=radius, fill=255)
    width, height = shot.width + 2 * margin, shot.height + 2 * margin

    canvas = Image.new("RGBA", (width, height))
    a, b = (Image.new("RGBA", (1, 1), c).getpixel((0, 0)) for c in (top, bottom))
    draw = ImageDraw.Draw(canvas)
    for y in range(height):
        t = y / (height - 1)
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(round(p + (q - p) * t) for p, q in zip(a, b, strict=True)),
        )

    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [margin, margin + 18, margin + shot.width, margin + shot.height + 18],
        radius=radius,
        fill=(0, 0, 0, 120),
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(28)))
    canvas.paste(shot, (margin, margin), mask)
    return canvas.convert("RGB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setFont(QFont("Segoe UI", 10))
    setTheme(Theme.LIGHT)
    setThemeColor("#0067c0")

    service = build_service()
    window = MainWindow(QIcon(str(data_path("icon.ico"))))
    window.setMicaEffectEnabled(False)  # Mica is composed by the OS, not by Qt
    fit = FitPresenter(window.fit, service, data_path("sample_reflections.csv"))
    line = LinePresenter(window.line, service)
    estimate = EstimatePresenter(window.estimate, service)
    window.fit.bind(fit)
    window.line.bind(line)
    window.estimate.bind(estimate)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.resize(*SIZE)
    window.show()
    settle(app)

    shots: dict[str, tuple[Image.Image, bool]] = {}

    def shoot(name: str, dark: bool) -> None:
        window.set_dark(dark)
        settle(app, 1.2)
        shots[name] = (grab(window, dark), dark)

    fit.open_sample()
    window.fit.dislocation_card.switch.setChecked(True)
    fit.calculate()
    shoot("fit-light", False)
    shoot("fit-dark", True)

    window.fit.tabs.setCurrentItem("table")
    window.fit.stack.setCurrentIndex(1)
    shoot("fit-table", False)
    window.fit.tabs.setCurrentItem("report")
    window.fit.stack.setCurrentIndex(2)
    window.fit.report.verticalScrollBar().setValue(260)
    shoot("fit-report", True)
    window.fit.tabs.setCurrentItem("plots")
    window.fit.stack.setCurrentIndex(0)

    window.switchTo(window.line)
    window.line.mode.setCurrentIndex(list(LineMode).index(LineMode.MICROSTRUCTURE))
    line.calculate()
    shoot("line", False)

    window.switchTo(window.estimate)
    estimate.calculate()
    shoot("estimate", True)

    for name, (shot, dark) in shots.items():
        target = OUT / f"demo-{name}.png"
        framed(shot, *BACKDROP[dark]).save(target, optimize=True)
        print(f"wrote {target}  {shot.width}x{shot.height}")
    window.close()


if __name__ == "__main__":
    main()
