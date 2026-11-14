"""The author's rules for degenerate lines: which reference model fills the gap."""

from __future__ import annotations

import math

import pytest

from sizeout_demo.domain import (
    InvalidInput,
    Quantity,
    ReferenceModelRequired,
    ReferenceModels,
    SizeStrain,
    Source,
)
from sizeout_demo.domain.microstructure import solutions

D, ES = Quantity(43.0, 1.2), Quantity(0.117, 0.003)
SCHERRER, MONSHI, STOKES = Quantity(44.0, 1.5), Quantity(47.5, 2.0), Quantity(0.13, 0.01)


def test_both_coefficients_positive_take_the_line() -> None:
    (only,) = solutions(D, ES, ReferenceModels(scherrer=SCHERRER))
    assert only == SizeStrain(D, ES, Source.LINE, Source.LINE)


def test_no_strain_takes_the_size_from_each_es0_model() -> None:
    found = solutions(D, None, ReferenceModels(scherrer=SCHERRER, monshi=MONSHI))
    assert [(s.size, s.strain.value, s.size_source) for s in found] == [
        (SCHERRER, 0.0, Source.SCHERRER),
        (MONSHI, 0.0, Source.MONSHI),
    ]


def test_no_strain_without_a_model_says_which_one_is_missing() -> None:
    with pytest.raises(ReferenceModelRequired, match="D0 of Scherrer"):
        solutions(D, None, ReferenceModels(stokes=STOKES))


def test_infinite_crystallite_takes_the_strain_from_stokes() -> None:
    (only,) = solutions(None, ES, ReferenceModels(stokes=STOKES))
    assert only.infinite
    assert (only.strain, only.strain_source) == (STOKES, Source.STOKES)


def test_infinite_crystallite_without_stokes_is_refused() -> None:
    with pytest.raises(ReferenceModelRequired, match="es_inf of Stokes"):
        solutions(None, ES, ReferenceModels(scherrer=SCHERRER))


def test_neither_broadening_is_an_infinite_unstrained_crystal() -> None:
    (only,) = solutions(None, None, ReferenceModels())
    assert math.isinf(only.size.value)
    assert only.strain.value == 0.0
    assert (only.size_source, only.strain_source) == (Source.ABSENT, Source.ABSENT)


@pytest.mark.parametrize("bad", [Quantity(0.0), Quantity(-1.0), Quantity(math.inf)])
def test_a_reference_model_must_be_finite_and_positive(bad: Quantity) -> None:
    with pytest.raises(InvalidInput):
        ReferenceModels(scherrer=bad)


def test_a_size_strain_pair_is_validated() -> None:
    with pytest.raises(InvalidInput):
        SizeStrain(Quantity(0.0), ES)
    with pytest.raises(InvalidInput):
        SizeStrain(D, Quantity(-0.1))


def test_quantity_refuses_nan_and_a_negative_esd() -> None:
    with pytest.raises(InvalidInput):
        Quantity(math.nan)
    with pytest.raises(InvalidInput):
        Quantity(1.0, -0.1)
    with pytest.raises(InvalidInput):
        Quantity(1.0, math.inf)
