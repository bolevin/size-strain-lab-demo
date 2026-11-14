"""The calculator, against the formulas written out once more here."""

from __future__ import annotations

import math

import pytest

from sizeout_demo.domain import (
    DislocationSettings,
    Instrument,
    InvalidInput,
    Origin,
    Profile,
    Quantity,
    from_densities,
    from_microstructure,
    from_widths,
)
from sizeout_demo.domain.estimation import total_width

INST = Instrument()
TTH = Quantity(38.4735, 0.01)
TH, DTH = math.radians(38.4735 / 2), math.radians(0.01 / 2)


def test_widths_from_size_and_strain() -> None:
    e = from_microstructure(
        Quantity(45.0, 2.0), Quantity(0.12, 0.01), TTH, INST, Profile.PSEUDO_VOIGT
    )
    size = math.degrees(0.94 * 0.1540598 / (45.0 * math.cos(TH)))
    strain = math.degrees(4.0 * 0.0012 * math.tan(TH))
    b = e.broadening
    assert b.size is not None
    assert b.strain is not None
    assert b.total is not None
    assert b.size.value == pytest.approx(size)
    assert b.size.esd == pytest.approx(size * math.hypot(2.0 / 45.0, DTH * math.tan(TH)))
    assert b.strain.value == pytest.approx(strain)
    assert b.strain.esd == pytest.approx(
        strain * math.hypot(0.01 / 0.12, DTH / (math.cos(TH) * math.sin(TH)))
    )
    assert b.total.value == pytest.approx((size + math.sqrt(size**2 + 4 * strain**2)) / 2)
    assert e.origin is Origin.MICROSTRUCTURE


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        (Profile.LORENTZ, 0.3),
        (Profile.GAUSS, math.hypot(0.2, 0.1)),
        (Profile.PSEUDO_VOIGT, (0.2 + math.sqrt(0.04 + 0.04)) / 2),
    ],
)
def test_total_width_per_profile(profile: Profile, expected: float) -> None:
    assert total_width(profile, Quantity(0.2), Quantity(0.1)).value == pytest.approx(
        expected
    )


@pytest.mark.parametrize("profile", list(Profile))
def test_total_width_limits(profile: Profile) -> None:
    """Either broadening alone is the total, for every profile."""
    assert total_width(profile, Quantity(0.2), Quantity(0.0)).value == pytest.approx(0.2)
    assert total_width(profile, Quantity(0.0), Quantity(0.1)).value == pytest.approx(0.1)
    assert total_width(profile, Quantity(0.0), Quantity(0.0)).value == 0.0


def test_an_absent_value_has_no_broadening_of_its_kind() -> None:
    e = from_microstructure(None, Quantity(0.12), TTH, INST, Profile.LORENTZ)
    assert e.size is not None
    assert e.size.is_infinite
    assert e.broadening.size == Quantity(0.0)
    assert e.broadening.total == e.broadening.strain


def test_widths_back_to_size_and_strain() -> None:
    e = from_microstructure(
        Quantity(45.0, 2.0), Quantity(0.12, 0.01), TTH, INST, Profile.GAUSS
    )
    assert e.broadening.size is not None
    back = from_widths(e.broadening.size, e.broadening.strain, TTH, INST, Profile.GAUSS)
    assert back.size is not None
    assert back.strain is not None
    assert back.size.value == pytest.approx(45.0)
    assert back.strain.value == pytest.approx(0.12)
    assert back.broadening.total == e.broadening.total


def test_densities_give_size_and_strain_each_alone() -> None:
    settings = DislocationSettings()
    e = from_densities(Quantity(1.5e11, 1e10), Quantity(2.0e10, 1e9), TTH, INST, settings)
    b = settings.burgers.vector().value
    assert e.size is not None
    assert e.strain is not None
    assert e.size.value == pytest.approx(math.sqrt(3e14 / 1.5e11))
    assert e.size.esd == pytest.approx(e.size.value * 1e10 / (2 * 1.5e11))
    assert e.strain.value == pytest.approx(math.sqrt(1e-10 * 2.0e10 / 12.0) * b)
    assert e.broadening.total is None
    assert e.burgers == settings.burgers.vector()


def test_rounding_the_inputs_of_the_calculator() -> None:
    e = from_microstructure(
        Quantity(45.27, 1.94),
        Quantity(0.1234, 0.0112),
        TTH,
        INST,
        Profile.PSEUDO_VOIGT,
        round_inputs=True,
    )
    assert e.size == Quantity(45.0, 2.0)
    assert e.strain == Quantity(0.12, 0.01)
    assert e.rounded


@pytest.mark.parametrize("two_theta", [0.0, 180.0, -5.0])
def test_the_angle_is_checked(two_theta: float) -> None:
    with pytest.raises(InvalidInput, match="2Theta"):
        from_microstructure(
            Quantity(45.0), None, Quantity(two_theta), INST, Profile.LORENTZ
        )


def test_something_has_to_be_set() -> None:
    with pytest.raises(InvalidInput, match="D and / or es"):
        from_microstructure(None, None, TTH, INST, Profile.LORENTZ)
    with pytest.raises(InvalidInput, match="FWHM_size"):
        from_widths(None, None, TTH, INST, Profile.LORENTZ)
    with pytest.raises(InvalidInput, match="Ldis_D"):
        from_densities(None, None, TTH, INST, DislocationSettings())
