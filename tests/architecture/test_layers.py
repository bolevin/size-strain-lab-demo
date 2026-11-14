"""The dependency rule of the architecture, held by a test.

The contracts live in ``pyproject.toml`` under ``[tool.importlinter]``: dependencies
point inwards, the calculation uses the standard library only, and the presenters
never touch Qt.  See docs/architecture.md, section 5.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "sizeout_demo"


def test_import_contracts_hold() -> None:
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from importlinter.cli import lint_imports; "
            "sys.exit(lint_imports())",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Contracts: 3 kept, 0 broken" in done.stdout


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text("utf-8"))):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            roots.add((node.module or "").split(".")[0])
    return roots


def test_domain_imports_nothing_but_the_standard_library() -> None:
    """A second, independent look: read the import statements themselves."""
    allowed = set(sys.stdlib_module_names) | {"sizeout_demo"}
    for path in (PACKAGE / "domain").glob("*.py"):
        assert _imported_roots(path) <= allowed, path.name


def test_presenters_parsing_and_view_import_no_qt() -> None:
    for name in ("presenters.py", "parsing.py", "view.py"):
        roots = _imported_roots(PACKAGE / "ui" / name)
        assert not roots & {"PySide6", "qfluentwidgets", "pyqtgraph", "numpy"}, name


def test_value_objects_are_immutable() -> None:
    """Every dataclass in the domain and the application is frozen."""
    for layer in ("domain", "application"):
        for path in (PACKAGE / layer).glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text("utf-8"))):
                for deco in getattr(node, "decorator_list", []):
                    if (
                        isinstance(deco, ast.Call)
                        and getattr(deco.func, "id", "") == "dataclass"
                    ):
                        keywords = {k.arg: k.value for k in deco.keywords}
                        frozen = keywords.get("frozen")
                        where = f"{path.name}: {getattr(node, 'name', '?')}"
                        assert isinstance(frozen, ast.Constant), where
                        assert frozen.value is True, where
