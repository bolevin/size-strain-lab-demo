"""The results as CSV - one row per solution, full precision, for a spreadsheet."""

from __future__ import annotations

import csv
import io
import math

from sizeout_demo.application import EstimateRun, FitRun, LineRun, MicrostructureRun, Run
from sizeout_demo.domain import Quantity, Solution, TechniqueResult

SOLUTION_COLUMNS = (
    "calculation",
    "technique",
    "profile",
    "A",
    "dA",
    "B",
    "dB",
    "R2",
    "n_points",
    "D_nm",
    "dD_nm",
    "es_pct",
    "des_pct",
    "D_source",
    "es_source",
    "Ldis_D",
    "dLdis_D",
    "Ldis_es",
    "dLdis_es",
    "Ldis",
    "dLdis",
    "Ro_total",
    "dRo_total",
)
ESTIMATE_COLUMNS = (
    "origin",
    "two_theta",
    "d_two_theta",
    "D_nm",
    "dD_nm",
    "es_pct",
    "des_pct",
    "FWHM_size",
    "dFWHM_size",
    "FWHM_strain",
    "dFWHM_strain",
    "FWHM_corr",
    "dFWHM_corr",
    "b_nm",
    "db_nm",
)


def _number(value: float) -> str:
    return "inf" if math.isinf(value) else repr(value)


def _pair(q: Quantity | None) -> list[str]:
    return ["", ""] if q is None else [_number(q.value), _number(q.esd)]


def _solution_row(
    kind: str, result: TechniqueResult | None, solution: Solution | None
) -> list[str]:
    row = [kind]
    if result is None:
        row += [""] * 8
    else:
        line = result.line
        row += [
            result.technique.short,
            result.profile.short,
            *_pair(line.intercept),
            *_pair(line.slope),
            "" if line.r_squared is None else _number(line.r_squared),
            str(line.n_points),
        ]
    if solution is None:
        return row + [""] * (len(SOLUTION_COLUMNS) - len(row))
    m, d = solution.microstructure, solution.densities
    row += [*_pair(m.size), *_pair(m.strain), m.size_source.name, m.strain_source.name]
    if d is None:
        return row + [""] * 8
    return [
        *row,
        *_pair(d.size_part),
        *_pair(d.strain_part),
        *_pair(d.williamson),
        *_pair(d.ashby),
    ]


def _rows(run: Run) -> tuple[tuple[str, ...], list[list[str]]]:
    if isinstance(run, EstimateRun):
        e, b = run.estimate, run.estimate.broadening
        return ESTIMATE_COLUMNS, [
            [
                e.origin.name,
                *_pair(e.two_theta),
                *_pair(e.size),
                *_pair(e.strain),
                *_pair(b.size),
                *_pair(b.strain),
                *_pair(b.total),
                *_pair(e.burgers),
            ]
        ]
    if isinstance(run, MicrostructureRun):
        return SOLUTION_COLUMNS, [_solution_row("microstructure", None, run.solution)]
    results = run.results if isinstance(run, FitRun) else (run.result,)
    kind = (
        "fit"
        if isinstance(run, FitRun)
        else (
            "two_reflections" if isinstance(run, LineRun) and run.points else "coefficients"
        )
    )
    rows = []
    for result in results:
        if not result.solutions:
            rows.append(_solution_row(kind, result, None))
        rows += [_solution_row(kind, result, s) for s in result.solutions]
    return SOLUTION_COLUMNS, rows


class CsvResultTable:
    """Implements :class:`sizeout_demo.application.TableRenderer`."""

    def render(self, run: Run) -> str:
        header, rows = _rows(run)
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
        return out.getvalue()
