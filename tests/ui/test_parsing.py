from __future__ import annotations

import re

import pytest

from sizeout_demo.domain import (
    CubicBurgers,
    Distribution,
    EnteredBurgers,
    Profile,
    Quantity,
)
from sizeout_demo.ui import parsing
from sizeout_demo.ui.parsing import InputError
from sizeout_demo.ui.view import (
    DislocationInput,
    InstrumentInput,
    PairInput,
    ReferenceInput,
)


def dislocation_input(**changes: object) -> DislocationInput:
    fields: dict[str, object] = {
        "enabled": True,
        "distribution": Distribution.ANISOTROPIC,
        "n": "1",
        "k": "12",
        "cubic": True,
        "a": PairInput("4.0495", ""),
        "m": "2",
        "uvw": ("1", "-1", "0"),
        "b": PairInput("0.2863", "0.0001"),
        "rounded": True,
    }
    fields.update(changes)
    return DislocationInput(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "value"),
    [("1.5", 1.5), (" 2,25 ", 2.25), ("1e-3", 1e-3), ("", None), ("  ", None)],
)
def test_number(text: str, value: float | None) -> None:
    assert parsing.number(text, "x") == value


@pytest.mark.parametrize(
    ("text", "message"),
    [("abc", "'abc' is not a number"), ("inf", "finite"), ("nan", "finite")],
)
def test_number_errors_name_the_field(text: str, message: str) -> None:
    with pytest.raises(InputError, match=re.escape(message)):
        parsing.number(text, "Wavelength")


def test_pair_empty_esd_is_zero_and_empty_value_is_not_set() -> None:
    assert parsing.pair(PairInput("45", ""), "D") == Quantity(45.0, 0.0)
    assert parsing.pair(PairInput("", "2"), "D") is None
    with pytest.raises(InputError, match=r"e\.s\.d\. of D must not be negative"):
        parsing.pair(PairInput("45", "-2"), "D")
    with pytest.raises(InputError, match="D is empty"):
        parsing.required_pair(PairInput("", ""), "D")


def test_positive_pair_treats_zero_as_not_set() -> None:
    assert parsing.positive_pair(PairInput("0", "1"), "D0") is None
    assert parsing.positive_pair(PairInput("-1", ""), "D0") is None


def test_instrument_and_references() -> None:
    inst = parsing.instrument(InstrumentInput("1.540598", "0.94", "4", Profile.GAUSS))
    assert (inst.wavelength, inst.k_size, inst.k_strain) == (1.540598, 0.94, 4.0)
    refs = parsing.references(
        ReferenceInput(PairInput("44", "1.5"), PairInput(), PairInput("0.13", ""))
    )
    assert (refs.scherrer, refs.monshi, refs.stokes) == (
        Quantity(44.0, 1.5),
        None,
        Quantity(0.13),
    )


def test_dislocations_switch_and_burgers_modes() -> None:
    assert parsing.dislocations(dislocation_input(enabled=False)) is None
    forced = parsing.dislocations(dislocation_input(enabled=False), force=True)
    assert forced is not None
    assert isinstance(forced.burgers, CubicBurgers)
    entered = parsing.dislocations(dislocation_input(cubic=False))
    assert entered is not None
    assert entered.burgers == EnteredBurgers(Quantity(0.2863, 0.0001))


def test_dislocation_integers() -> None:
    with pytest.raises(InputError, match="m must be a whole number"):
        parsing.dislocations(dislocation_input(m="2.5"))
