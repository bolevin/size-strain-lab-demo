"""Plain files on disk."""

from __future__ import annotations

from pathlib import Path


class FileTextStore:
    """Implements :class:`sizeout_demo.application.TextStore`: UTF-8, LF line ends."""

    def save(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8", newline="\n")
