"""Ports: what the use cases need from the outside world.

The application owns these interfaces; adapters implement them.  Another input
format or another report layout is one new adapter - no use case and no line of
the calculation changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from sizeout_demo.application.runs import ReflectionData, Run


class ReflectionFormatError(Exception):
    """The file was read, but it is not a reflection list in the expected format."""


class ReflectionReader(Protocol):
    def read(self, path: Path) -> ReflectionData:
        """Parse ``path``.  Raises OSError, ReflectionFormatError or InvalidInput."""
        ...


class ReportRenderer(Protocol):
    def render(self, run: Run) -> str:
        """The finished calculation as a human-readable document."""
        ...


class TableRenderer(Protocol):
    def render(self, run: Run) -> str:
        """The finished calculation as a machine-readable table."""
        ...


class TextStore(Protocol):
    def save(self, path: Path, text: str) -> None:
        """Persist ``text``.  Raises OSError."""
        ...
