"""Dislocation densities - the author's 16.00 table and the edge cases."""

from __future__ import annotations

import math

import pytest

from sizeout_demo.domain import (
    CubicBurgers,
    DislocationSettings,
    Distribution,
    EnteredBurgers,
    InvalidInput,
    Quantity,
    SizeStrain,
    densities,
)

EXACT = DislocationSettings(burgers=EnteredBurgers(Quantity(0.384)), round_inputs=False)


def test_the_authors_table() -> None:
    """The worked example of the full program's specification.

    D 240 +- 18 nm, es 0.0147487 +- 0.0026817 %, b 0.384 nm, Coeff 3, n 1, k 12; the
    e.s.d. of Ro_total is the root of the sum of squares, sqrt(7.8125e8^2 + 6.4374e7^2).
    """
    d = densities(SizeStrain(Quantity(240.0, 18.0), Quantity(0.0147487, 0.0026817)), EXACT)
    assert (d.size_part.value, d.size_part.esd) == pytest.approx(
        (5.208e9, 7.813e8), rel=1e-3
    )
    assert (d.strain_part.value, d.strain_part.esd) == pytest.approx(
        (1.770e8, 6.437e7), rel=1e-3
    )
    assert (d.williamson.value, d.williamson.esd) == pytest.approx(
        (9.602e8, 1.889e8), rel=1e-3
    )
    assert (d.ashby.value, d.ashby.esd) == pytest.approx((5.385e9, 7.839e8), rel=1e-3)
    assert d.cf == pytest.approx(6.0)
    assert d.distribution == "anisotropic"


def test_the_total_is_cf_es_over_b_d() -> None:
    m = SizeStrain(Quantity(80.0, 4.0), Quantity(0.2, 0.01))
    settings = DislocationSettings(
        n=2.0,
        distribution=Distribution.ISOTROPIC,
        k=6.0,
        burgers=EnteredBurgers(Quantity(0.25)),
        round_inputs=False,
    )
    d = densities(m, settings)
    assert d.cf is not None
    assert d.cf == pytest.approx(math.sqrt(6.0 * 1))  # n cancels
    # Ldis = Cf * es/(b D) in 1/nm^2 -> 1/cm^2: es in % (1e-2), nm^-2 = 1e14 cm^-2
    assert d.williamson.value == pytest.approx(d.cf * 0.2e-2 / (0.25 * 80.0) * 1e14)


def test_infinite_size_leaves_only_the_strain_part() -> None:
    m = SizeStrain(Quantity(math.inf), Quantity(0.08, 0.005))
    d = densities(m, EXACT)
    assert d.size_part.value == 0.0
    assert d.williamson == d.strain_part == d.ashby
    assert d.cf is None
    assert d.distribution == "any"


def test_no_strain_leaves_only_the_size_part_and_needs_no_burgers_vector() -> None:
    settings = DislocationSettings(
        burgers=EnteredBurgers(Quantity(0.0)), round_inputs=False
    )
    d = densities(SizeStrain(Quantity(50.0, 2.0), Quantity(0.0)), settings)
    assert d.williamson == d.size_part == d.ashby
    assert d.strain_part.value == 0.0


def test_strain_needs_a_burgers_vector() -> None:
    settings = DislocationSettings(burgers=EnteredBurgers(Quantity(0.0)))
    with pytest.raises(InvalidInput, match="Burgers"):
        densities(SizeStrain(Quantity(50.0), Quantity(0.1)), settings)


def test_cubic_burgers_vector() -> None:
    b = CubicBurgers(Quantity(4.0495, 0.0005), m=2, uvw=(1, -1, 0)).vector()
    assert b.value == pytest.approx(0.40495 / 2 * math.sqrt(2))
    assert b.esd == pytest.approx(0.00005 / 2 * math.sqrt(2))


def test_rounding_first_uses_the_published_values() -> None:
    m = SizeStrain(Quantity(43.283, 1.256), Quantity(0.11707, 0.00292))
    d = densities(m, DislocationSettings())
    assert d.used_size.quantity == Quantity(43.0, 1.0)
    assert d.used_strain.quantity == Quantity(0.117, 0.003)
    assert d.size_part.value == pytest.approx(3e14 / 43.0**2)


@pytest.mark.parametrize(
    "kwargs",
    [{"n": 0.0}, {"k": 1.5}, {"k": 25.0}, {"n": math.nan}],
)
def test_settings_are_validated(kwargs: dict[str, float]) -> None:
    with pytest.raises(InvalidInput):
        DislocationSettings(**kwargs)  # type: ignore[arg-type]


def test_k_of_exactly_six_over_pi_is_allowed() -> None:
    assert DislocationSettings(k=6.0 / math.pi).k == pytest.approx(1.9099, abs=1e-4)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"a": Quantity(0.0)},
        {"a": Quantity(4.0), "m": 0},
        {"a": Quantity(4.0), "uvw": (0, 0, 0)},
    ],
)
def test_cubic_cell_is_validated(kwargs: dict[str, object]) -> None:
    with pytest.raises(InvalidInput):
        CubicBurgers(**kwargs)  # type: ignore[arg-type]
