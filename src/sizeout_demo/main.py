"""Composition root: the only place that knows every concrete class."""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

from sizeout_demo import APP_NAME, __version__
from sizeout_demo.adapters import (
    CsvReflectionReader,
    CsvResultTable,
    FileTextStore,
    PlainTextReport,
)
from sizeout_demo.application import SizeStrainService


def data_path(name: str) -> Path:
    """A file shipped inside the package (also inside the frozen .exe)."""
    return Path(str(resources.files("sizeout_demo") / "data" / name))


def build_service() -> SizeStrainService:
    return SizeStrainService(
        CsvReflectionReader(), PlainTextReport(), CsvResultTable(), FileTextStore()
    )


def _selftest() -> int:
    """Fit the bundled sample and check the result is the one the tests pin."""
    from sizeout_demo.domain import AnalysisSettings, DislocationSettings

    service = build_service()
    run = service.fit(
        service.load(data_path("sample_reflections.csv")),
        AnalysisSettings(dislocations=DislocationSettings()),
    )
    whp = run.results[0].solutions[0].microstructure
    ok = abs(whp.size.value - 43.2830) < 1e-3 and abs(whp.strain.value - 0.117071) < 1e-5
    print(
        f"SELFTEST {'OK' if ok else 'FAIL'}  WHP D = {whp.size.value:.4f} nm, "
        f"es = {whp.strain.value:.6f} %"
    )
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="size-strain-lab",
        description=f"{APP_NAME}: crystallite size and microstrain from line widths",
    )
    parser.add_argument("reflections", nargs="?", type=Path, help="reflection list to open")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--selftest", action="store_true", help="verify the build and exit")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()

    # Qt is imported here so that --selftest and --version need no display
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication
    from qfluentwidgets import Theme, setTheme, setThemeColor

    from sizeout_demo.ui.main_window import MainWindow
    from sizeout_demo.ui.presenters import EstimatePresenter, FitPresenter, LinePresenter

    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(sys.argv[:1])
    app.setFont(QFont("Segoe UI", 10))
    setTheme(Theme.AUTO)
    setThemeColor("#0067c0")

    service = build_service()
    window = MainWindow(QIcon(str(data_path("icon.ico"))))
    fit = FitPresenter(window.fit, service, data_path("sample_reflections.csv"))
    line = LinePresenter(window.line, service)
    estimate = EstimatePresenter(window.estimate, service)
    window.fit.bind(fit)
    window.line.bind(line)
    window.estimate.bind(estimate)
    window.presenters = (fit, line, estimate)  # the connections do not keep them alive
    window.show()
    if args.reflections is not None:
        fit.load(args.reflections)
    return int(app.exec())


if __name__ == "__main__":
    sys.exit(main())
