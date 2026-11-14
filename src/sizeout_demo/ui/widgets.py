"""Building blocks shared by the pages: cards, number fields, the input groups."""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    CheckBox,
    ComboBox,
    IconWidget,
    InfoBarIcon,
    LineEdit,
    StrongBodyLabel,
    SwitchButton,
    isDarkTheme,
    setFont,
)

from sizeout_demo.domain import Distribution, Profile
from sizeout_demo.ui.view import (
    DislocationInput,
    InstrumentInput,
    Metric,
    PairInput,
    ReferenceInput,
    Tone,
)

MUTED = ("#6b6b6b", "#a6a6a6")  # light theme, dark theme
ACCENT = ("#0067c0", "#4cc2ff")
EMPTY = "—"
PLUS_MINUS = "±"


def titled_card(title: str) -> tuple[CardWidget, QVBoxLayout]:
    card = CardWidget()
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 12, 16, 14)
    layout.setSpacing(8)
    layout.addWidget(StrongBodyLabel(title))
    return card, layout


def caption(text: str) -> CaptionLabel:
    label = CaptionLabel(text)
    label.setTextColor(*MUTED)
    label.setWordWrap(True)
    return label


class NumberEdit(LineEdit):
    def __init__(self, text: str = "", placeholder: str = "", width: int = 92) -> None:
        super().__init__()
        self.setText(text)
        self.setPlaceholderText(placeholder)
        self.setFixedWidth(width)
        self.setClearButtonEnabled(False)


class PairRow:
    """A value and its e.s.d. in one grid row: caption, value, ±, e.s.d., unit."""

    def __init__(
        self,
        grid: QGridLayout,
        row: int,
        text: str,
        *,
        unit: str = "",
        value: str = "",
        esd: str = "",
        placeholder: str = "",
    ) -> None:
        self.value = NumberEdit(value, placeholder)
        self.esd = NumberEdit(esd, "0", width=72)
        grid.addWidget(BodyLabel(text), row, 0)
        grid.addWidget(self.value, row, 1)
        grid.addWidget(caption(PLUS_MINUS), row, 2)
        grid.addWidget(self.esd, row, 3)
        grid.addWidget(caption(unit), row, 4)

    def input(self) -> PairInput:
        return PairInput(self.value.text(), self.esd.text())

    def set(self, value: str, esd: str = "") -> None:
        self.value.setText(value)
        self.esd.setText(esd)

    def widgets(self) -> tuple[QWidget, ...]:
        return self.value, self.esd


def pair_grid() -> QGridLayout:
    grid = QGridLayout()
    grid.setHorizontalSpacing(6)
    grid.setVerticalSpacing(6)
    grid.setColumnStretch(0, 1)
    return grid


class MetricCard(CardWidget):
    """Caption, a large value, and a line of context underneath."""

    def __init__(self, caption_text: str) -> None:
        super().__init__()
        self.setMinimumHeight(96)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        self.caption = CaptionLabel(caption_text)
        self.caption.setTextColor(*MUTED)
        self.value = BodyLabel(EMPTY)
        setFont(self.value, 21, QFont.Weight.DemiBold)
        self.value.setTextColor(*ACCENT)
        self.hint = CaptionLabel("")
        self.hint.setTextColor(*MUTED)
        layout.addWidget(self.caption)
        layout.addStretch(1)
        layout.addWidget(self.value)
        layout.addWidget(self.hint)

    def show_metric(self, metric: Metric | None) -> None:
        if metric is not None:
            self.caption.setText(metric.caption)
        self.value.setText(metric.value if metric else EMPTY)
        self.hint.setText(metric.hint if metric else "")


class NoticeBar(QFrame):
    """A remark on the result: a missing model, two solutions, no total."""

    _FILL: ClassVar = {
        Tone.WARNING: ("#fff4ce", "#433519"),
        Tone.NEUTRAL: ("#e8f1fb", "#1f2f40"),
    }
    _ICON: ClassVar = {
        Tone.WARNING: InfoBarIcon.WARNING,
        Tone.NEUTRAL: InfoBarIcon.INFORMATION,
    }

    def __init__(self) -> None:
        super().__init__()
        self._tone = Tone.NEUTRAL
        self.icon = IconWidget()
        self.icon.setFixedSize(16, 16)
        self.text = BodyLabel("")
        self.text.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.text, 1)
        self.hide()

    def show_notice(self, text: str, tone: Tone) -> None:
        if not text:
            self.hide()
            return
        self._tone = tone
        self.icon.setIcon(self._ICON[tone])
        self.text.setText(text)
        self.show()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        light, dark = self._FILL[self._tone]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(dark if isDarkTheme() else light))
        painter.drawRoundedRect(self.rect(), 6, 6)


class InstrumentCard(CardWidget):
    """Profile, wavelength and the constants of the broadening equations."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(8)
        layout.addWidget(StrongBodyLabel("Profile and radiation"))
        self.profile = ComboBox()
        for profile in Profile:
            self.profile.addItem(profile.value, userData=profile)
        self.profile.setCurrentIndex(list(Profile).index(Profile.PSEUDO_VOIGT))
        self.wavelength = NumberEdit("1.540598")
        self.k_size = NumberEdit("0.94")
        self.k_strain = NumberEdit("4")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        rows = (
            ("Reflection profile", self.profile, ""),
            ("Wavelength λ", self.wavelength, "Å"),
            ("K_size (Scherrer)", self.k_size, ""),
            ("K_strain", self.k_strain, ""),
        )
        for row, (text, widget, unit) in enumerate(rows):
            grid.addWidget(BodyLabel(text), row, 0)
            grid.addWidget(widget, row, 1)
            grid.addWidget(caption(unit), row, 2)
        grid.setColumnStretch(0, 1)
        layout.addLayout(grid)

    def input(self) -> InstrumentInput:
        return InstrumentInput(
            self.wavelength.text(),
            self.k_size.text(),
            self.k_strain.text(),
            self.profile.currentData(),
        )


class ReferenceCard(CardWidget):
    """The models a degenerate line falls back on; empty fields are "not entered"."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(8)
        layout.addWidget(StrongBodyLabel("Reference models"))
        layout.addWidget(
            caption(
                "Used only when the line shows no strain (D from an "
                "es = 0 model) or no size broadening (es from Stokes)."
            )
        )
        grid = pair_grid()
        self.scherrer = PairRow(
            grid, 0, "D0, Scherrer", unit="nm", placeholder="not entered"
        )
        self.monshi = PairRow(grid, 1, "D0, Monshi", unit="nm", placeholder="not entered")
        self.stokes = PairRow(
            grid, 2, "es_inf, Stokes", unit="%", placeholder="not entered"
        )
        layout.addLayout(grid)

    def input(self) -> ReferenceInput:
        return ReferenceInput(
            self.scherrer.input(), self.monshi.input(), self.stokes.input()
        )


class DislocationCard(CardWidget):
    """Williamson-Smallman / Ashby parameters, behind an on/off switch."""

    def __init__(
        self, *, switchable: bool = True, title: str = "Dislocation density"
    ) -> None:
        super().__init__()
        self._switchable = switchable
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(StrongBodyLabel(title))
        head.addStretch(1)
        self.switch = SwitchButton()
        self.switch.setOnText("On")
        self.switch.setOffText("Off")
        head.addWidget(self.switch)
        self.switch.setVisible(switchable)
        layout.addLayout(head)

        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(6)
        self.distribution = ComboBox()
        self.distribution.addItem(
            "anisotropic (Coeff = 3)", userData=Distribution.ANISOTROPIC
        )
        self.distribution.addItem("isotropic (Coeff = 1)", userData=Distribution.ISOTROPIC)
        self.n = NumberEdit("1")
        self.k = NumberEdit("12")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.addWidget(BodyLabel("Distribution"), 0, 0)
        grid.addWidget(self.distribution, 0, 1, 1, 2)
        grid.addWidget(BodyLabel("n, at the boundary"), 1, 0)
        grid.addWidget(self.n, 1, 1)
        grid.addWidget(BodyLabel("k, strain distribution"), 2, 0)
        grid.addWidget(self.k, 2, 1)
        grid.addWidget(caption("6/π … 24"), 2, 2)
        grid.setColumnStretch(0, 1)
        body.addLayout(grid)

        self.burgers_mode = ComboBox()
        self.burgers_mode.addItem("b = a/m [u v w], cubic cell", userData=True)
        self.burgers_mode.addItem("b typed in", userData=False)
        body.addWidget(self.burgers_mode)

        self.cubic = QWidget()
        cubic = pair_grid()
        cubic.setContentsMargins(0, 0, 0, 0)
        self.a = PairRow(cubic, 0, "a", unit="Å", value="4.0495")
        self.m = NumberEdit("2", width=44)
        self.u, self.v, self.w = (NumberEdit(t, width=44) for t in ("1", "-1", "0"))
        indices = QHBoxLayout()
        indices.setSpacing(6)
        indices.addWidget(BodyLabel("m"))
        indices.addWidget(self.m)
        indices.addSpacing(8)
        indices.addWidget(BodyLabel("[u v w]"))
        for edit in (self.u, self.v, self.w):
            indices.addWidget(edit)
        indices.addStretch(1)
        cubic.addLayout(indices, 1, 0, 1, 5)
        self.cubic.setLayout(cubic)
        self.entered = QWidget()
        entered = pair_grid()
        entered.setContentsMargins(0, 0, 0, 0)
        self.b = PairRow(entered, 0, "b", unit="nm", value="0.2863")
        self.entered.setLayout(entered)
        body.addWidget(self.cubic)
        body.addWidget(self.entered)
        self.rounded = CheckBox("Round D, es and b as published first")
        self.rounded.setChecked(True)
        body.addWidget(self.rounded)
        layout.addWidget(self.body)

        self.burgers_mode.currentIndexChanged.connect(self._burgers_changed)
        self.switch.checkedChanged.connect(self.body.setVisible)
        self._burgers_changed()
        self.body.setVisible(not switchable)

    def _burgers_changed(self) -> None:
        cubic = bool(self.burgers_mode.currentData())
        self.cubic.setVisible(cubic)
        self.entered.setVisible(not cubic)

    def input(self) -> DislocationInput:
        return DislocationInput(
            enabled=self.switch.isChecked() or not self._switchable,
            distribution=self.distribution.currentData(),
            n=self.n.text(),
            k=self.k.text(),
            cubic=bool(self.burgers_mode.currentData()),
            a=self.a.input(),
            m=self.m.text(),
            uvw=(self.u.text(), self.v.text(), self.w.text()),
            b=self.b.input(),
            rounded=self.rounded.isChecked(),
        )
