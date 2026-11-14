"""The text report and the CSV table for every kind of run."""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path

from sizeout_demo.adapters import CsvResultTable, PlainTextReport
from sizeout_demo.adapters.csv_table import ESTIMATE_COLUMNS, SOLUTION_COLUMNS
from sizeout_demo.application import EstimateRequest, SizeStrainService
from sizeout_demo.domain import (
    AnalysisSettings,
    DislocationSettings,
    Instrument,
    Line,
    Origin,
    Point,
    Profile,
    Quantity,
    ReferenceModels,
    SizeStrain,
    Technique,
)

REPORT, TABLE = PlainTextReport(), CsvResultTable()


def rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def test_fit_report_and_table(service: SizeStrainService, sample_path: Path) -> None:
    run = service.fit(
        service.load(sample_path), AnalysisSettings(dislocations=DislocationSettings())
    )
    text = REPORT.render(run)
    for expected in (
        "fit of reflection widths",
        "Reflections (9, 8 used)",
        "331        112.0237     0.71651   no",
        "Williamson-Hall plot (pseudo-Voigt)",
        "Size-strain plot (pseudo-Voigt)",
        "D   = 43 ± 1 nm",
        "Ro_total",
        "Cf           6",
        "(rounded as published)",
    ):
        assert expected in text, expected
    table = rows(TABLE.render(run))
    assert [r["technique"] for r in table] == ["WHP", "SSP"]
    assert float(table[0]["D_nm"]) == run.results[0].solutions[0].microstructure.size.value
    assert float(table[0]["Ro_total"]) > float(table[0]["Ldis"])
    assert list(table[0]) == list(SOLUTION_COLUMNS)


def test_two_models_give_two_rows(service: SizeStrainService) -> None:
    settings = AnalysisSettings(
        references=ReferenceModels(Quantity(44.0, 1.5), Quantity(47.5, 2.0))
    )
    run = service.from_line(
        Line(Quantity(3.3e-3, 1e-4), Quantity(-2e-7, 1e-7)), Technique.WHP, settings
    )
    text = REPORT.render(run)
    assert "Solution 1 of 2" in text
    assert "from the Monshi-Scherrer model (es = 0)" in text
    table = rows(TABLE.render(run))
    assert [(r["D_nm"], r["D_source"]) for r in table] == [
        ("44.0", "SCHERRER"),
        ("47.5", "MONSHI"),
    ]


def test_a_missing_model_is_in_the_report(service: SizeStrainService) -> None:
    run = service.from_line(
        Line(Quantity(-4e-4), Quantity(1.2e-6)), Technique.WHP, AnalysisSettings()
    )
    assert "No solution: The size coefficient is <= 0" in REPORT.render(run)
    (row,) = rows(TABLE.render(run))
    assert row["D_nm"] == ""


def test_two_reflections_report_lists_the_points(service: SizeStrainService) -> None:
    run = service.from_two_reflections(
        Point(Quantity(1e-4, 4e-6), Quantity(3.5e-3, 8e-5)),
        Point(Quantity(9.6e-4, 1.2e-5), Quantity(4.67e-3, 9e-5)),
        Technique.WHP,
        AnalysisSettings(profile=Profile.PSEUDO_VOIGT),
    )
    text = REPORT.render(run)
    assert "two reflections" in text
    assert "point 2" in text
    assert rows(TABLE.render(run))[0]["calculation"] == "two_reflections"


def test_microstructure_run(service: SizeStrainService) -> None:
    run = service.from_microstructure(
        SizeStrain(Quantity(math.inf), Quantity(0.08, 0.005)), DislocationSettings()
    )
    text = REPORT.render(run)
    assert "D   = ∞ nm" in text
    assert "any" in text
    assert rows(TABLE.render(run))[0]["D_nm"] == "inf"


def test_estimate_run(service: SizeStrainService) -> None:
    run = service.estimate(
        EstimateRequest(
            Origin.DENSITIES,
            Quantity(1.5e11, 1e10),
            Quantity(2e10, 1e9),
            Quantity(38.4735, 0.01),
            (1, 1, 1),
            Instrument(),
            Profile.PSEUDO_VOIGT,
            DislocationSettings(),
            rounded=False,
        )
    )
    text = REPORT.render(run)
    assert "estimate from Ldis_D and Ldis_es" in text
    assert "FWHM_corr    not calculated" in text
    (row,) = rows(TABLE.render(run))
    assert list(row) == list(ESTIMATE_COLUMNS)
    assert row["FWHM_corr"] == ""
    assert float(row["b_nm"]) > 0
