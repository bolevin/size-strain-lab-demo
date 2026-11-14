"""The report as plain text: what was calculated, from what, and how it was rounded."""

from __future__ import annotations

from sizeout_demo import APP_NAME, __version__
from sizeout_demo.application import (
    EstimateRun,
    FitRun,
    LineRun,
    MicrostructureRun,
    Run,
)
from sizeout_demo.application.formatting import (
    INFINITY,
    burgers_text,
    esd_text,
    power_text,
    size_text,
    strain_text,
)
from sizeout_demo.domain import (
    AnalysisSettings,
    Densities,
    DislocationSettings,
    Instrument,
    Quantity,
    Solution,
    Source,
    TechniqueResult,
    linearization,
)

RULE = "-" * 72


def _heading(text: str) -> list[str]:
    return ["", text, "-" * len(text)]


def _instrument(inst: Instrument) -> str:
    return (
        f"lambda = {inst.wavelength:g} A,  K_size = {inst.k_size:g},  "
        f"K_strain = {inst.k_strain:g}"
    )


def _full(q: Quantity) -> str:
    return INFINITY if q.is_infinite else esd_text(q)


def _dislocation_settings(s: DislocationSettings) -> str:
    return (
        f"{s.distribution.label} (Coeff = {s.distribution.coeff}), n = {s.n:g}, "
        f"k = {s.k:g}, b = {burgers_text(s.burgers.vector())} nm"
    )


def _densities(d: Densities, s: DislocationSettings) -> list[str]:
    lines = [
        "  Dislocation density, 1/cm^2 (Williamson & Smallman, 1956)",
        f"    parameters   {_dislocation_settings(s)}",
        f"    Ldis_D       {power_text(d.size_part)}      due to the size",
        f"    Ldis_es      {power_text(d.strain_part)}      due to the strain",
        f"    Ldis         {power_text(d.williamson)}      sqrt(Ldis_D * Ldis_es), "
        f"{d.distribution}",
        f"    Ro_total     {power_text(d.ashby)}      Ldis_D + Ldis_es (Ashby, 1970)",
    ]
    if d.cf is not None:
        lines.append(f"    Cf           {d.cf:.6g}      Ldis = Cf * es / (b * D)")
    if s.round_inputs:
        lines.append(
            f"    values used  D = {_used(d.used_size.quantity, d.used_size.decimals)} nm, "
            f"es = {_used(d.used_strain.quantity, d.used_strain.decimals)} %, "
            f"b = {_used(d.used_burgers.quantity, d.used_burgers.decimals)} nm "
            "(rounded as published)"
        )
    return lines


def _used(q: Quantity, decimals: int | None) -> str:
    if q.is_infinite:
        return INFINITY
    if decimals is None:
        return f"{q.value:.6g}"
    places = max(decimals, 0)
    return f"{q.value:.{places}f} ± {q.esd:.{places}f}"


def _solution(
    index: int, total: int, solution: Solution, dislocations: DislocationSettings | None
) -> list[str]:
    m = solution.microstructure
    lines = [] if total == 1 else [f"  Solution {index} of {total}"]
    size_note = "" if m.size_source is Source.LINE else f"   from the {m.size_source.value}"
    strain_note = (
        "" if m.strain_source is Source.LINE else f"   from the {m.strain_source.value}"
    )
    lines += [
        f"  D   = {size_text(m.size)} nm      ({_full(m.size)}){size_note}",
        f"  es  = {strain_text(m.strain)} %      ({_full(m.strain)}){strain_note}",
    ]
    if solution.densities is not None and dislocations is not None:
        lines += _densities(solution.densities, dislocations)
    return lines


def _technique(result: TechniqueResult, settings: AnalysisSettings) -> list[str]:
    plot = linearization(result.technique, result.profile)
    line = result.line
    lines = _heading(f"{result.technique.value} ({result.profile.value})")
    lines.append(f"  x = {plot.x_label},  y = {plot.y_label}")
    fit = f"  A = {esd_text(line.intercept)}     B = {esd_text(line.slope)}"
    if line.r_squared is not None:
        fit += f"     R^2 = {line.r_squared:.5f}  ({line.n_points} reflections)"
    lines.append(fit)
    if result.problem:
        lines.append(f"  No solution: {result.problem}")
        return lines
    for index, solution in enumerate(result.solutions, start=1):
        lines += _solution(index, len(result.solutions), solution, settings.dislocations)
    return lines


def _header(kind: str) -> list[str]:
    title = f"{APP_NAME} {__version__} - {kind}"
    return [title, "=" * len(title)]


def _fit(run: FitRun) -> list[str]:
    s = run.settings
    used = sum(r.use for r in run.reflections)
    lines = _header("fit of reflection widths")
    lines += [
        f"Data         {run.source.name}" + (f"  -  {run.title}" if run.title else ""),
        f"Profile      {s.profile.value}",
        f"Radiation    {_instrument(s.instrument)}",
    ]
    lines += _heading(f"Reflections ({len(run.reflections)}, {used} used)")
    lines.append("  hkl      2Theta, deg   FWHM, deg   used")
    lines += [
        f"  {r.label:<6} {r.two_theta:12.4f} {r.fwhm:11.5f}   {'yes' if r.use else 'no'}"
        for r in run.reflections
    ]
    for result in run.results:
        lines += _technique(result, s)
    return lines


def _line(run: LineRun) -> list[str]:
    lines = _header(f"D and es from the {run.entry.value}")
    lines += [
        f"Profile      {run.settings.profile.value}",
        f"Radiation    {_instrument(run.settings.instrument)}",
    ]
    if run.points is not None:
        lines += _heading("Two reflections on the plot")
        lines += [
            f"  point {i}   x = {esd_text(p.x)}   y = {esd_text(p.y)}"
            for i, p in enumerate(run.points, start=1)
        ]
    return lines + _technique(run.result, run.settings)


def _microstructure(run: MicrostructureRun) -> list[str]:
    lines = _header("dislocation density from D and es")
    lines += _heading("Microstructure as entered")
    return lines + _solution(1, 1, run.solution, run.dislocations)


def _estimate(run: EstimateRun) -> list[str]:
    r, e = run.request, run.estimate
    b = e.broadening
    lines = _header(f"estimate from {e.origin.value}")
    hkl = "".join(str(i) for i in r.hkl) if r.hkl else "-"
    lines += [
        f"Reflection   2Theta = {esd_text(e.two_theta)} deg, hkl {hkl}",
        f"Profile      {r.profile.value}",
        f"Radiation    {_instrument(r.instrument)}",
    ]
    if r.dislocations is not None:
        lines.append(f"Dislocations {_dislocation_settings(r.dislocations)}")
    lines += _heading("Microstructure")
    lines.append(f"  D   = {_full(e.size) if e.size is not None else 'not estimated'} nm")
    lines.append(
        f"  es  = {_full(e.strain) if e.strain is not None else 'not estimated'} %"
    )
    lines += _heading("Broadening without the instrument, deg")
    for caption, width in (
        ("FWHM_size", b.size),
        ("FWHM_strain", b.strain),
        ("FWHM_corr", b.total),
    ):
        lines.append(
            f"  {caption:<12} {esd_text(width) if width is not None else 'not calculated'}"
        )
    if e.rounded:
        lines.append("  (D, es and b rounded as published before use)")
    return lines


def render_lines(run: Run) -> list[str]:
    if isinstance(run, FitRun):
        return _fit(run)
    if isinstance(run, LineRun):
        return _line(run)
    if isinstance(run, MicrostructureRun):
        return _microstructure(run)
    return _estimate(run)


class PlainTextReport:
    """Implements :class:`sizeout_demo.application.ReportRenderer`."""

    def render(self, run: Run) -> str:
        return "\n".join([*render_lines(run), "", RULE, ""])


__all__ = ["PlainTextReport"]
