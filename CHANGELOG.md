# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-15

### Added

- Fit of reflection widths on the Williamson-Hall and the size-strain plot side by side,
  for Lorentz, Gauss and pseudo-Voigt profiles, with e.s.d.'s and R².
- Exclusion of a reflection by a click on its point or its check box, with an immediate
  refit.
- D and e from a line typed in, from a line through two reflections, or typed in.
- Reference models (Scherrer, Monshi-Scherrer, Stokes-Wilson) for lines that show no
  strain or no size broadening; two es = 0 models give two solutions.
- Dislocation density after Williamson and Smallman and after Ashby, with the Burgers
  vector typed in or from a cubic cell, optionally from values rounded as published.
- A broadening calculator: widths from D and e, D and e from widths or from densities.
- Text report and CSV table for every calculation; light and dark theme.
- Synthetic sample, golden master from the full program, property tests, a mutation
  check, arc42 documentation and ADRs.
