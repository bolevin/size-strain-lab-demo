"""The six plots: where a reflection lands, and what the coefficients mean."""

from __future__ import annotations

import math

import pytest

from sizeout_demo.domain import (
    LINEARIZATIONS,
    Instrument,
    Line,
    Profile,
    Quantity,
    Reflection,
    Technique,
    linearization,
)

INST = Instrument(wavelength=1.5406, k_size=0.94, k_strain=4.0)
K_LAMBDA = 0.94 * 0.15406  # nm
REFLECTION = Reflection(two_theta=60.0, fwhm=0.5)
BETA = math.radians(0.5)


def test_there_is_one_strategy_per_technique_and_profile() -> None:
    assert len(LINEARIZATIONS) == 6
    for (technique, profile), plot in LINEARIZATIONS.items():
        assert (plot.technique, plot.profile) == (technique, profile)
        assert plot.x_label
        assert plot.y_label


def test_williamson_hall_points_at_theta_30() -> None:
    cos30 = math.cos(math.radians(30))
    whp_lor = linearization(Technique.WHP, Profile.LORENTZ).point(REFLECTION, INST)
    assert whp_lor == pytest.approx((4.0 * 0.5, BETA * cos30))
    whp_gau = linearization(Technique.WHP, Profile.GAUSS).point(REFLECTION, INST)
    assert whp_gau == pytest.approx((4.0, (BETA * cos30) ** 2))
    whp_pv = linearization(Technique.WHP, Profile.PSEUDO_VOIGT).point(REFLECTION, INST)
    assert whp_pv == pytest.approx((4.0 / (BETA * cos30), BETA * cos30))


def test_size_strain_points_at_theta_30() -> None:
    d = 0.15406 / (2 * 0.5)  # nm, Bragg's law at theta 30
    reduced = d * BETA * math.cos(math.radians(30)) / 0.15406
    ssp_lor = linearization(Technique.SSP, Profile.LORENTZ).point(REFLECTION, INST)
    assert ssp_lor == pytest.approx((0.94 * d, reduced))
    ssp_gau = linearization(Technique.SSP, Profile.GAUSS).point(REFLECTION, INST)
    assert ssp_gau == pytest.approx(((0.94 * d) ** 2, reduced**2))
    ssp_pv = linearization(Technique.SSP, Profile.PSEUDO_VOIGT).point(REFLECTION, INST)
    assert ssp_pv == pytest.approx((0.94 * d * reduced, reduced**2))


@pytest.mark.parametrize(
    ("technique", "profile", "line", "size", "strain"),
    [
        # WHP: D = K lambda / A or / sqrt(A); es = 100 B or 100 sqrt(B)
        (
            Technique.WHP,
            Profile.LORENTZ,
            (3e-3, 3e-4, 1e-3, 1e-4),
            (K_LAMBDA / 3e-3, K_LAMBDA / 3e-3 * 0.1),
            (0.1, 0.01),
        ),
        (
            Technique.WHP,
            Profile.GAUSS,
            (9e-6, 9e-7, 1e-6, 1e-7),
            (K_LAMBDA / 3e-3, K_LAMBDA / 3e-3 * 0.05),
            (0.1, 0.005),
        ),
        (
            Technique.WHP,
            Profile.PSEUDO_VOIGT,
            (3e-3, 3e-4, 1e-6, 1e-7),
            (K_LAMBDA / 3e-3, K_LAMBDA / 3e-3 * 0.1),
            (0.1, 0.005),
        ),
        # SSP: D = 1/B or 1/sqrt(B); es = 200 A / K_strain or 200 sqrt(A) / K_strain
        (
            Technique.SSP,
            Profile.LORENTZ,
            (2e-3, 2e-4, 0.025, 0.001),
            (40.0, 1.6),
            (0.1, 0.01),
        ),
        (
            Technique.SSP,
            Profile.GAUSS,
            (4e-6, 4e-7, 6.25e-4, 2.5e-5),
            (40.0, 0.8),
            (0.1, 0.005),
        ),
        (
            Technique.SSP,
            Profile.PSEUDO_VOIGT,
            (4e-6, 4e-7, 0.025, 0.001),
            (40.0, 1.6),
            (0.1, 0.005),
        ),
    ],
)
def test_coefficients_to_size_and_strain(
    technique: Technique,
    profile: Profile,
    line: tuple[float, float, float, float],
    size: tuple[float, float],
    strain: tuple[float, float],
) -> None:
    a, da, b, db = line
    d, e = linearization(technique, profile).microstructure(
        Line(Quantity(a, da), Quantity(b, db)), INST
    )
    assert d is not None
    assert e is not None
    assert (d.value, d.esd) == pytest.approx(size)
    assert (e.value, e.esd) == pytest.approx(strain)


@pytest.mark.parametrize("profile", list(Profile))
def test_a_non_positive_coefficient_means_that_broadening_is_absent(
    profile: Profile,
) -> None:
    whp = linearization(Technique.WHP, profile)
    assert whp.microstructure(Line(Quantity(-1e-3), Quantity(1e-6)), INST)[0] is None
    assert whp.microstructure(Line(Quantity(1e-3), Quantity(0.0)), INST)[1] is None
    ssp = linearization(Technique.SSP, profile)
    assert ssp.microstructure(Line(Quantity(1e-6), Quantity(-0.02)), INST)[0] is None
    assert ssp.microstructure(Line(Quantity(-1e-6), Quantity(0.02)), INST)[1] is None
