"""Golden master: the same inputs through the full SizeOut program.

``tests/golden/full_program_reference.json`` is written by ``tools/make_golden.py``
from SizeOut 16.01, which keeps its numbers in single precision as the original
QuickBASIC program did - hence the tolerance of a few parts in ten million.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pytest

from sizeout_demo.application import ReflectionData
from sizeout_demo.domain import (
    AnalysisSettings,
    CubicBurgers,
    DislocationSettings,
    Distribution,
    EnteredBurgers,
    Instrument,
    Line,
    Profile,
    Quantity,
    ReferenceModels,
    SizeStrain,
    Technique,
    analyse_reflections,
    densities,
    from_densities,
    from_microstructure,
    from_widths,
    round_burgers,
    round_size,
    round_strain,
    solve,
)

GOLDEN = json.loads(
    (Path(__file__).parents[1] / "golden" / "full_program_reference.json").read_text(
        "utf-8"
    )
)
SINGLE = 3e-6  # relative: seven digits of the single-precision program
PROFILE = {"Lor": Profile.LORENTZ, "Gau": Profile.GAUSS, "pV": Profile.PSEUDO_VOIGT}
TECHNIQUE = {"WHP": Technique.WHP, "SSP": Technique.SSP}


def close(got: float, expected: float, rel: float = SINGLE) -> bool:
    if math.isinf(got):
        return expected == 0.0  # the full program writes the infinite size as 0
    return math.isclose(got, expected, rel_tol=rel, abs_tol=1e-12)


def ids(cases: list[dict[str, Any]]) -> list[str]:
    return [
        f"{c.get('case', '')} {c.get('technique', '')} {c.get('profile', '')}".strip()
        for c in cases
    ]


def test_the_reference_was_made_from_this_sample(sample_path: Path) -> None:
    assert GOLDEN["sample_sha256"] == hashlib.sha256(sample_path.read_bytes()).hexdigest()
    assert GOLDEN["reference"].startswith("SizeOut 16.01")


FITS = [f for f in GOLDEN["fits"] if (f["technique"], f["profile"]) != ("SSP", "Lor")]


@pytest.mark.parametrize("case", FITS, ids=ids(FITS))
def test_fit_of_the_sample(case: dict[str, Any], sample: ReflectionData) -> None:
    technique, profile = TECHNIQUE[case["technique"]], PROFILE[case["profile"]]
    (result,) = analyse_reflections(
        sample.reflections, AnalysisSettings(profile=profile), techniques=[technique]
    )
    line = result.line
    assert close(line.intercept.value, case["a"], 1e-12)  # the fit is in double there
    assert close(line.slope.value, case["b"], 1e-12)
    assert close(line.intercept.esd, case["da"], 1e-12)
    assert close(line.slope.esd, case["db"], 1e-12)
    assert close(line.r_squared or 0.0, case["r2"], 1e-12)
    m = result.solutions[0].microstructure
    for got, key in (
        (m.size.value, "D"),
        (m.size.esd, "dD"),
        (m.strain.value, "es"),
        (m.strain.esd, "des"),
    ):
        assert close(got, case[key]), key


def test_the_lorentz_size_strain_fit_differs_on_purpose(sample: ReflectionData) -> None:
    """The full program's Lor-SSP drops cos(theta) from y; its line slopes the wrong way
    for this sample and reads as an infinite crystallite.  The demo's does not."""
    (full,) = [
        f for f in GOLDEN["fits"] if (f["technique"], f["profile"]) == ("SSP", "Lor")
    ]
    assert full["fallback"] == "infinite_d"
    (ours,) = analyse_reflections(
        sample.reflections,
        AnalysisSettings(profile=Profile.LORENTZ),
        techniques=[Technique.SSP],
    )
    assert ours.line.slope.value > 0
    assert 40.0 < ours.solutions[0].microstructure.size.value < 70.0


def _references(case: dict[str, Any]) -> ReferenceModels:
    def model(key: str) -> Quantity | None:
        return Quantity(*case[key]) if key in case else None

    return ReferenceModels(model("scherrer"), model("monshi"), model("stokes"))


@pytest.mark.parametrize("case", GOLDEN["lines"], ids=ids(GOLDEN["lines"]))
def test_line_to_size_and_strain(case: dict[str, Any]) -> None:
    inp = case["input"]
    line = Line(Quantity(inp["a"], inp["da"]), Quantity(inp["b"], inp["db"]))
    settings = AnalysisSettings(
        profile=PROFILE[case["profile"]], references=_references(inp)
    )
    result = solve(line, TECHNIQUE[case["technique"]], settings)
    expected = case["solutions"]
    if expected[0]["D"] == -1.0 or expected[0]["es"] == -1.0:  # a model not entered
        assert result.problem
        assert not result.solutions
        return
    assert not result.problem
    assert len(result.solutions) == len(expected)
    for solution, full in zip(result.solutions, expected, strict=True):
        m = solution.microstructure
        assert close(m.size.value, full["D"])
        assert close(m.strain.value, full["es"])
        assert close(m.size.esd, abs(full["dD"]))
        assert close(m.strain.esd, abs(full["des"]))


def _settings(case: dict[str, Any]) -> DislocationSettings:
    burgers = (
        CubicBurgers(Quantity(*case["a"]))
        if "a" in case
        else EnteredBurgers(Quantity(*case["b"]))
    )
    distribution = (
        Distribution.ANISOTROPIC if case["coeff"] == 3 else Distribution.ISOTROPIC
    )
    return DislocationSettings(
        n=case["n"],
        distribution=distribution,
        k=case["k"],
        burgers=burgers,
        round_inputs=case["round"],
    )


@pytest.mark.parametrize("case", GOLDEN["dislocations"], ids=ids(GOLDEN["dislocations"]))
def test_dislocation_density(case: dict[str, Any]) -> None:
    inp = case["input"]
    size = Quantity(math.inf) if inp["D"][0] == 0.0 else Quantity(*inp["D"])
    d = densities(SizeStrain(size, Quantity(*inp["es"])), _settings(inp))
    pairs = (
        (d.size_part, "ldis_d"),
        (d.strain_part, "ldis_es"),
        (d.williamson, "ldis"),
        (d.ashby, "ro_total"),
    )
    for q, key in pairs:
        assert close(q.value, case[key]), key
        assert close(q.esd, case[f"d_{key}"]), key
    assert close(d.cf or 0.0, case["cf"])
    assert d.distribution == case["distribution"]


@pytest.mark.parametrize("case", GOLDEN["estimates"], ids=ids(GOLDEN["estimates"]))
def test_calculator(case: dict[str, Any]) -> None:
    inp = case["input"]
    first = Quantity(*inp["first"]) if inp["first"] else None
    second = Quantity(*inp["second"]) if inp["second"] else None
    tth, profile, rounded = Quantity(*inp["tth"]), PROFILE[inp["profile"]], inp["round"]
    inst = Instrument()
    if inp["group"] == "micro":
        e = from_microstructure(first, second, tth, inst, profile, round_inputs=rounded)
    elif inp["group"] == "widths":
        e = from_widths(first, second, tth, inst, profile, round_results=rounded)
    else:
        settings = DislocationSettings(burgers=CubicBurgers(Quantity(4.0495, 0.0005)))
        e = from_densities(first, second, tth, inst, settings, round_values=rounded)
    b = e.broadening
    pairs = (
        (e.size, "D", "dD"),
        (e.strain, "es", "des"),
        (b.size, "size", "d_size"),
        (b.strain, "strain", "d_strain"),
        (b.total, "corr", "d_corr"),
    )
    for q, key, dkey in pairs:
        if q is None:
            assert case[key] == -1.0, key  # the full program's "not calculated"
            continue
        assert close(q.value, case[key]), key
        assert close(q.esd, case[dkey]), dkey


@pytest.mark.parametrize(
    ("kind", "rounder"),
    [("size", round_size), ("strain", round_strain), ("burgers", round_burgers)],
)
def test_rounding(kind: str, rounder: Any) -> None:
    for value, esd, r_value, r_esd in GOLDEN["rounding"][kind]:
        got = rounder(Quantity(value, esd)).quantity
        assert (got.value, got.esd) == pytest.approx((r_value, r_esd), rel=1e-6), value
