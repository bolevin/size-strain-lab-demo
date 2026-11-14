from __future__ import annotations

from pathlib import Path

import pytest

from sizeout_demo.adapters import CsvReflectionReader
from sizeout_demo.application import ReflectionData, ReflectionFormatError

READER = CsvReflectionReader()


def test_the_sample(sample: ReflectionData) -> None:
    assert sample.title.startswith("Synthetic fcc phase")
    assert len(sample.reflections) == 9
    first = sample.reflections[0]
    assert (first.hkl, first.two_theta, first.fwhm, first.use) == (
        (1, 1, 1),
        38.4735,
        0.24141,
        True,
    )
    assert [r.label for r in sample.reflections if not r.use] == ["331"]


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
def test_delimiters_and_aliases(delimiter: str) -> None:
    text = (
        delimiter.join(["2Theta", "FWHM_corr"])
        + "\n"
        + delimiter.join(["40", "0.3"])
        + "\n"
        + delimiter.join(["60", "0.4"])
        + "\n"
    )
    data = READER.parse(text, default_title="plain")
    assert [(r.two_theta, r.fwhm, r.hkl, r.use) for r in data.reflections] == [
        (40.0, 0.3, None, True),
        (60.0, 0.4, None, True),
    ]
    assert data.title == "plain"


def test_comments_title_and_blank_lines() -> None:
    data = READER.parse(
        "# title:  Zinc oxide \n\n# a remark\nh,k,l,two_theta,fwhm,use\n"
        "1,0,0,31.77,0.21,0\n"
    )
    assert data.title == "Zinc oxide"
    assert data.reflections[0].use is False


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "no header"),
        ("two_theta,width\n40,0.3\n", "no 'fwhm' column"),
        ("two_theta,fwhm\n", "no reflections"),
        ("two_theta,fwhm\n40,abc\n", "line 2: 2Theta and FWHM must be numbers"),
        ("two_theta,fwhm\n40,-0.3\n", "line 2: FWHM"),
        ("two_theta,fwhm\n200,0.3\n", "line 2: 2Theta"),
        ("h,k,l,two_theta,fwhm\n1,x,1,40,0.3\n", "integers"),
        ("two_theta,fwhm,use\n40,0.3,maybe\n", "'use' must be 1 or 0"),
    ],
)
def test_errors_name_the_line(text: str, message: str) -> None:
    with pytest.raises(ReflectionFormatError, match=message):
        READER.parse(text)


def test_a_file_on_disk(tmp_path: Path) -> None:
    path = tmp_path / "zno.csv"
    path.write_text("﻿two_theta,fwhm\n31.8,0.2\n34.4,0.21\n36.3,0.22\n", encoding="utf-8")
    data = READER.read(path)
    assert data.title == "zno"  # the stem, when there is no title line
    assert len(data.reflections) == 3
