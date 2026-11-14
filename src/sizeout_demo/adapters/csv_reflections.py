"""Reflection lists as CSV: a header row, one reflection per line.

    # title: Synthetic fcc phase, Cu K-alpha-1
    h,k,l,two_theta,fwhm,use
    1,1,1,38.4723,0.27154,1

Required columns: ``two_theta`` and ``fwhm`` (degrees, the FWHM already corrected
for the instrument).  Optional: ``h``, ``k``, ``l`` and ``use`` (1/0).  Lines that
start with ``#`` are comments; ``# title:`` names the data set.  Comma, semicolon
or tab separate the fields.
"""

from __future__ import annotations

import csv
from pathlib import Path

from sizeout_demo.application import ReflectionData, ReflectionFormatError
from sizeout_demo.domain import InvalidInput, Reflection

_ALIASES = {
    "two_theta": "two_theta",
    "2theta": "two_theta",
    "2th": "two_theta",
    "tth": "two_theta",
    "fwhm": "fwhm",
    "fwhm_corr": "fwhm",
    "h": "h",
    "k": "k",
    "l": "l",
    "use": "use",
}
_TRUE, _FALSE = {"1", "yes", "y", "true", "+"}, {"0", "no", "n", "false", "-"}


def _flag(text: str, line: int) -> bool:
    value = text.strip().lower()
    if value in _TRUE or value == "":
        return True
    if value in _FALSE:
        return False
    raise ReflectionFormatError(f"line {line}: 'use' must be 1 or 0, not {text!r}")


class CsvReflectionReader:
    """Implements :class:`sizeout_demo.application.ReflectionReader`."""

    def read(self, path: Path) -> ReflectionData:
        text = path.read_text(encoding="utf-8-sig")
        return self.parse(text, default_title=path.stem)

    def parse(self, text: str, default_title: str = "") -> ReflectionData:
        title = default_title
        rows: list[tuple[int, str]] = []
        for number, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                body = line[1:].strip()
                if body.lower().startswith("title:"):
                    title = body[6:].strip()
                continue
            rows.append((number, line))
        if not rows:
            raise ReflectionFormatError("the file holds no header and no reflections")
        header_line, header = rows[0]
        delimiter = max(",;\t", key=header.count)
        names = [
            _ALIASES.get(n.strip().lower(), "")
            for n in next(csv.reader([header], delimiter=delimiter))
        ]
        for needed in ("two_theta", "fwhm"):
            if needed not in names:
                raise ReflectionFormatError(
                    f"line {header_line}: the header has no '{needed}' column"
                )
        reflections = tuple(
            self._reflection(dict(zip(names, fields, strict=False)), number)
            for number, fields in (
                (n, next(csv.reader([t], delimiter=delimiter))) for n, t in rows[1:]
            )
        )
        if not reflections:
            raise ReflectionFormatError("the file has a header but no reflections")
        return ReflectionData(title, reflections)

    @staticmethod
    def _reflection(fields: dict[str, str], line: int) -> Reflection:
        try:
            two_theta, fwhm = float(fields["two_theta"]), float(fields["fwhm"])
        except (KeyError, ValueError):
            raise ReflectionFormatError(
                f"line {line}: 2Theta and FWHM must be numbers"
            ) from None
        hkl = None
        if all(fields.get(i, "").strip() for i in "hkl"):
            try:
                hkl = (int(fields["h"]), int(fields["k"]), int(fields["l"]))
            except ValueError:
                raise ReflectionFormatError(
                    f"line {line}: h, k, l must be integers"
                ) from None
        try:
            return Reflection(two_theta, fwhm, hkl, _flag(fields.get("use", ""), line))
        except InvalidInput as error:
            raise ReflectionFormatError(f"line {line}: {error}") from None
