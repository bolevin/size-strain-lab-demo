"""Plant known bugs, one at a time, and check that the tests catch every one.

    python tools/mutation_check.py

A test that never fails proves nothing.  Each mutation below is a mistake that is
easy to make in this code - a dropped factor, a tangent in the wrong place, a
rounding mode - and the suite must go red on each.  The source is copied to a temporary
folder for every run; the working tree is never touched.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = "src/sizeout_demo"


@dataclass(frozen=True)
class Mutation:
    name: str
    path: str
    old: str
    new: str
    tests: str = "tests"


MUTATIONS = [
    Mutation(
        "SSP-Lorentz without cos(theta), as in the full program's fit mode",
        f"{PKG}/domain/linearization.py",
        "return d, d * reflection.beta * math.cos(reflection.theta) / lam",
        "return d, d * reflection.beta / lam",
        "tests/domain",
    ),
    Mutation(
        "residual variance over n - 1",
        f"{PKG}/domain/regression.py",
        "s2 = ss_res / (n - 2)",
        "s2 = ss_res / (n - 1)",
        "tests/domain",
    ),
    Mutation(
        "Gauss size as for Lorentz",
        f"{PKG}/domain/linearization.py",
        "    Profile.GAUSS: _reciprocal_root,",
        "    Profile.GAUSS: _reciprocal,",
        "tests/domain",
    ),
    Mutation(
        "intercept e.s.d. of two points without the x1 term",
        f"{PKG}/domain/regression.py",
        "math.hypot(first.y.esd, x1 * d_slope, slope * first.x.esd)",
        "math.hypot(first.y.esd, x1 * d_slope)",
        "tests/domain",
    ),
    Mutation(
        "no strain keeps the line's size",
        f"{PKG}/domain/microstructure.py",
        "SizeStrain(d0, ZERO, source, Source.ABSENT)",
        "SizeStrain(size, ZERO, source, Source.ABSENT)",
        "tests/domain",
    ),
    Mutation(
        "Ldis_es without F = n",
        f"{PKG}/domain/dislocations.py",
        "value = 1e10 * s.k / s.n * (strain.value / b.value) ** 2",
        "value = 1e10 * s.k * (strain.value / b.value) ** 2",
        "tests/domain",
    ),
    Mutation(
        "Ashby's e.s.d. summed, not in quadrature",
        f"{PKG}/domain/dislocations.py",
        "ashby=Quantity(ld.value + le.value, math.hypot(ld.esd, le.esd)),",
        "ashby=Quantity(ld.value + le.value, ld.esd + le.esd),",
        "tests/domain",
    ),
    Mutation(
        "pseudo-Voigt total without the factor 4",
        f"{PKG}/domain/estimation.py",
        "root = math.sqrt(s * s + 4.0 * t * t)",
        "root = math.sqrt(s * s + t * t)",
        "tests/domain",
    ),
    Mutation(
        "strain width e.s.d. with tan(theta) instead of 1/(cos sin)",
        f"{PKG}/domain/estimation.py",
        "strain.value, dth / (math.cos(th) * math.sin(th))),",
        "strain.value, dth * math.tan(th)),",
        "tests/domain",
    ),
    Mutation(
        "rounding half even",
        f"{PKG}/domain/rounding.py",
        "rounding=ROUND_HALF_UP)",
        "rounding=ROUND_HALF_EVEN)",
        "tests/domain",
    ),
    Mutation(
        "rounding the binary value",
        f"{PKG}/domain/rounding.py",
        'return Decimal(f"{value:.12g}")',
        "return Decimal(value)",
        "tests/domain",
    ),
    Mutation(
        "an empty 'use' means not used",
        f"{PKG}/adapters/csv_reflections.py",
        'if value in _TRUE or value == "":',
        "if value in _TRUE:",
        "tests/adapters",
    ),
    Mutation(
        "the report without the rounding note",
        f"{PKG}/adapters/text_report.py",
        '"(rounded as published)"',
        '""',
        "tests/adapters",
    ),
    Mutation(
        "toggling a reflection does not refit",
        f"{PKG}/ui/presenters.py",
        "        if self._run is not None:\n            self.calculate()",
        "        pass",
        "tests/ui/test_presenters.py",
    ),
    Mutation(
        "the fitted line drawn from the first point",
        f"{PKG}/ui/presenters.py",
        "line=(0.0, line.at(0.0), x1, line.at(x1)),",
        "line=(min(xs), line.at(min(xs)), x1, line.at(x1)),",
        "tests/ui/test_presenters.py",
    ),
    Mutation(
        "no decimal comma",
        f"{PKG}/ui/parsing.py",
        'cleaned = text.strip().replace(",", ".")',
        "cleaned = text.strip()",
        "tests/ui/test_parsing.py",
    ),
    Mutation(
        "the calculation imports numpy",
        f"{PKG}/domain/quantity.py",
        "import math\n",
        "import math\n\nimport numpy\n",
        "tests/architecture",
    ),
]


def run(mutation: Mutation, scratch: Path) -> bool:
    """True if the tests failed - the mutation was caught."""
    tree = scratch / "tree"
    if tree.exists():
        shutil.rmtree(tree)
    for part in ("src", "tests", "pyproject.toml"):
        source = ROOT / part
        if source.is_dir():
            shutil.copytree(
                source, tree / part, ignore=shutil.ignore_patterns("__pycache__")
            )
        else:
            shutil.copy2(source, tree / part)
    target = tree / mutation.path
    text = target.read_text("utf-8")
    if text.count(mutation.old) != 1:
        sys.exit(f"{mutation.name}: the text to replace is not unique in {mutation.path}")
    target.write_text(text.replace(mutation.old, mutation.new), "utf-8")
    env = {**os.environ, "PYTHONPATH": str(tree / "src"), "QT_QPA_PLATFORM": "offscreen"}
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-x",
            "-q",
            "-p",
            "no:cacheprovider",
            mutation.tests,
        ],
        cwd=tree,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode != 0


def main() -> int:
    survived = []
    with tempfile.TemporaryDirectory(prefix="mutation_") as folder:
        for mutation in MUTATIONS:
            caught = run(mutation, Path(folder))
            print(f"{'caught  ' if caught else 'SURVIVED'}  {mutation.name}")
            if not caught:
                survived.append(mutation.name)
    print(f"\n{len(MUTATIONS) - len(survived)} of {len(MUTATIONS)} mutations caught")
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
