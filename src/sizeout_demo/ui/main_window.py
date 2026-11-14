"""The Fluent window: three calculation pages, About, and the theme switch."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    FluentWindow,
    NavigationItemPosition,
    Theme,
    isDarkTheme,
    setTheme,
)
from qfluentwidgets import FluentIcon as Icon

from sizeout_demo import APP_NAME, __version__
from sizeout_demo.ui.pages import EstimatePage, FitPage, LinePage
from sizeout_demo.ui.widgets import titled_card

ABOUT = f"""\
{APP_NAME} {__version__}

A small crystallite and a strained lattice both widen a diffraction line - the first
as 1/cos(theta), the second as tan(theta).  Plotting the widths of several
reflections so that the two dependences become a straight line separates them:
the crystallite size D comes from one coefficient of the line and the
microstrain es from the other.

  - Williamson-Hall plot (WHP) and size-strain plot (SSP), side by side;
  - Lorentz, Gauss and pseudo-Voigt reflection profiles;
  - e.s.d.'s of D and es from those of the fit;
  - reference models for a line that shows no strain or no size broadening;
  - dislocation density after Williamson & Smallman (1956) and Ashby (1970);
  - a calculator from D and es to the broadening of a reflection, and back;
  - results rounded as they would be published.

This is a demonstration written from scratch after SizeOut by A. A. Levin
(SizeCr package, DOI 10.13140/RG.2.2.15922.89280).  The full program reads the
output of SizeCr, writes its listing and data files byte for byte as the
original QuickBASIC program did, and has a richer interface.

Free software under the GNU General Public License, version 3 or later.
"""


class AboutPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("aboutPage")
        card, box = titled_card("About")
        text = BodyLabel(ABOUT)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.addWidget(text)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 24)
        layout.addWidget(card)
        layout.addStretch(1)


class MainWindow(FluentWindow):
    def __init__(self, icon: QIcon | None = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        if icon is not None:
            self.setWindowIcon(icon)
        self.resize(1360, 860)
        self.setMinimumSize(1180, 720)
        self.presenters: tuple[object, ...] = ()  # kept alive by the window

        self.fit = FitPage()
        self.line = LinePage()
        self.estimate = EstimatePage()
        self.about = AboutPage()
        self.addSubInterface(self.fit, Icon.MARKET, "Fit reflections")
        self.addSubInterface(self.line, Icon.EDIT, "From a line or D, es")
        self.addSubInterface(self.estimate, Icon.CALORIES, "Broadening calculator")
        self.addSubInterface(self.about, Icon.INFO, "About", NavigationItemPosition.BOTTOM)
        self.navigationInterface.addItem(
            routeKey="theme",
            icon=Icon.CONSTRACT,
            text="Light / dark",
            onClick=self.toggle_theme,
            selectable=False,
            position=NavigationItemPosition.BOTTOM,
        )
        self.fit.set_dark(isDarkTheme())

    def toggle_theme(self) -> None:
        self.set_dark(not isDarkTheme())

    def set_dark(self, dark: bool) -> None:
        setTheme(Theme.DARK if dark else Theme.LIGHT)
        self.fit.set_dark(dark)
        for page in (self.line, self.estimate):
            page.notice.update()
