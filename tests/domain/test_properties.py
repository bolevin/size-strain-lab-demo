"""Properties that must hold for any input, not only for the examples.

The first is the strongest check in the repository: widths computed by the
calculator's forward model from a known D and es, fitted by each of the six
linearizations, must give that D and es back.  The two halves of the program are
written from different equations, so they can only agree if both are right.
"""

from __future__ import annotations

import math
import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from sizeout_demo.domain import (
    LINEARIZATIONS,
    AnalysisSettings,
    DislocationSettings,
    EnteredBurgers,
    Instrument,
    Profile,
    Quantity,
    Reflection,
    SizeStrain,
    Technique,
    analyse_reflections,
    densities,
    fit_line,
    from_microstructure,
    from_widths,
    round_size,
    round_strain,
)

sizes = st.floats(min_value=5.0, max_value=500.0)
strains = st.floats(min_value=0.01, max_value=1.0)
angle_sets = st.lists(
    st.floats(min_value=15.0, max_value=150.0), min_size=3, max_size=10, unique=True
).filter(lambda a: max(a) - min(a) > 5.0)
instruments = st.builds(
    Instrument,
    wavelength=st.sampled_from([0.709317, 1.540598, 1.788965]),
    k_size=st.floats(0.8, 1.1),
    k_strain=st.sampled_from([4.0, 5.0]),
)
profiles = st.sampled_from(list(Profile))
esds = st.floats(min_value=0.0, max_value=0.2)


def exact_reflections(
    size: float, strain: float, angles: list[float], inst: Instrument, profile: Profile
) -> list[Reflection]:
    out = []
    for tt in angles:
        total = from_microstructure(
            Quantity(size), Quantity(strain), Quantity(tt), inst, profile
        ).broadening.total
        assert total is not None
        out.append(Reflection(tt, total.value))
    return out


@settings(max_examples=150, deadline=None)
@given(sizes, strains, angle_sets, instruments, profiles)
def test_round_trip_through_every_linearization(
    size: float, strain: float, angles: list[float], inst: Instrument, profile: Profile
) -> None:
    reflections = exact_reflections(size, strain, angles, inst, profile)
    for result in analyse_reflections(reflections, AnalysisSettings(inst, profile)):
        (solution,) = result.solutions
        m = solution.microstructure
        assert math.isclose(m.size.value, size, rel_tol=1e-7), result.technique
        assert math.isclose(m.strain.value, strain, rel_tol=1e-7), result.technique
        assert result.line.r_squared is not None
        assert result.line.r_squared > 1 - 1e-9


def test_all_six_linearizations_are_covered_by_the_round_trip() -> None:
    covered = {(t, p) for t in Technique for p in Profile}
    assert covered == set(LINEARIZATIONS)


@settings(max_examples=100, deadline=None)
@given(sizes, strains, angle_sets, profiles, st.randoms(use_true_random=False))
def test_the_order_of_the_reflections_does_not_matter(
    size: float, strain: float, angles: list[float], profile: Profile, rng: random.Random
) -> None:
    inst = Instrument()
    reflections = exact_reflections(size, strain, angles, inst, profile)
    noisy = [
        Reflection(r.two_theta, r.fwhm * (1 + rng.uniform(-0.05, 0.05)))
        for r in reflections
    ]
    shuffled = noisy[:]
    rng.shuffle(shuffled)
    first = analyse_reflections(noisy, AnalysisSettings(inst, profile))
    second = analyse_reflections(shuffled, AnalysisSettings(inst, profile))
    for a, b in zip(first, second, strict=True):
        assert math.isclose(a.line.slope.value, b.line.slope.value, rel_tol=1e-9)
        assert math.isclose(a.line.intercept.esd, b.line.intercept.esd, rel_tol=1e-9)


@settings(max_examples=150, deadline=None)
@given(sizes, strains, st.floats(10.0, 160.0), profiles, esds, esds)
def test_calculator_round_trip(
    size: float, strain: float, tth: float, profile: Profile, rel_d: float, rel_e: float
) -> None:
    inst = Instrument()
    forward = from_microstructure(
        Quantity(size, size * rel_d),
        Quantity(strain, strain * rel_e),
        Quantity(tth),
        inst,
        profile,
    )
    back = from_widths(
        forward.broadening.size, forward.broadening.strain, Quantity(tth), inst, profile
    )
    assert back.size is not None
    assert back.strain is not None
    assert math.isclose(back.size.value, size, rel_tol=1e-9)
    assert math.isclose(back.strain.value, strain, rel_tol=1e-9)
    assert math.isclose(back.size.esd, size * rel_d, rel_tol=1e-6, abs_tol=1e-12)


@settings(max_examples=150, deadline=None)
@given(
    sizes,
    strains,
    esds,
    esds,
    st.floats(0.15, 0.5),
    st.floats(1.0, 4.0),
    st.floats(2.0, 24.0),
)
def test_density_relations(
    size: float, strain: float, rel_d: float, rel_e: float, b: float, n: float, k: float
) -> None:
    m = SizeStrain(Quantity(size, size * rel_d), Quantity(strain, strain * rel_e))
    d = densities(
        m,
        DislocationSettings(
            n=n, k=k, burgers=EnteredBurgers(Quantity(b)), round_inputs=False
        ),
    )
    low, high = sorted((d.size_part.value, d.strain_part.value))
    assert low * (1 - 1e-12) <= d.williamson.value <= high * (1 + 1e-12)  # geometric mean
    assert math.isclose(
        d.williamson.value**2, d.size_part.value * d.strain_part.value, rel_tol=1e-9
    )
    assert math.isclose(d.ashby.value, d.size_part.value + d.strain_part.value)
    assert d.ashby.esd <= d.size_part.esd + d.strain_part.esd + 1e-6


@settings(max_examples=200, deadline=None)
@given(st.floats(0.5, 1e4), st.floats(1e-4, 50.0))
def test_rounding_stays_within_half_a_unit(value: float, esd: float) -> None:
    for rounder in (round_size, round_strain):
        once = rounder(Quantity(value, esd))
        assert once.decimals is not None
        half_unit = 0.5 * 10.0**-once.decimals
        assert abs(once.quantity.value - value) <= half_unit + 1e-12 * value


@settings(max_examples=200, deadline=None)
@given(st.floats(0.5, 1e4), st.floats(1e-4, 50.0))
def test_rounding_a_published_size_again_changes_nothing(value: float, esd: float) -> None:
    once = round_size(Quantity(value, esd))
    assert round_size(once.quantity).quantity == once.quantity


def test_the_strain_rule_is_not_idempotent_at_a_carry() -> None:
    """Found by the property above when it covered es too, and kept as a record.

    0.995 +- 0.045: two digits of es carry to 1.0, and des - which would round away
    to 0.0 - keeps one digit, 0.05.  Rounded again, 1.0 allows one decimal, and 0.05
    goes half up to 0.1.  The full program follows the same rule and does the same.
    """
    once = round_strain(Quantity(0.995, 0.045)).quantity
    assert (once.value, once.esd) == pytest.approx((1.0, 0.05))
    again = round_strain(once).quantity
    assert (again.value, again.esd) == pytest.approx((1.0, 0.1))


@settings(max_examples=100, deadline=None)
@given(
    st.lists(
        st.tuples(st.floats(-100, 100), st.floats(-100, 100)),
        min_size=3,
        max_size=12,
        unique_by=lambda p: round(p[0], 3),
    ),
    st.floats(0.1, 10.0),
)
def test_scaling_y_scales_the_line(points: list[tuple[float, float]], c: float) -> None:
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    if max(xs) - min(xs) < 1e-3:
        return
    a, b = fit_line(xs, ys), fit_line(xs, [c * y for y in ys])
    assert math.isclose(b.slope.value, c * a.slope.value, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(
        b.intercept.value, c * a.intercept.value, rel_tol=1e-9, abs_tol=1e-9
    )
