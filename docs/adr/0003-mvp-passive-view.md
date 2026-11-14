# 3. Model-View-Presenter with a passive view

Date: 2026-11-14 · Status: accepted

## Context

Most of what can go wrong in a desktop program happens between the user's input and
the calculation: a decimal comma, an empty field, a reflection toggled after the
fit. Testing that through real widgets is slow and brittle.

## Decision

Each page has a presenter (`ui/presenters.py`) and a view contract
(`ui/view.py`, a `Protocol`). The view hands over the text the user typed; the
presenter parses it (`ui/parsing.py`), calls the use case and hands back view models
with text already formatted. The window decides nothing.

`presenters`, `parsing` and `view` may not import Qt - an `import-linter` contract.

## Consequences

* Every intent - load, calculate, toggle a reflection, export, every error message -
  is tested against a fake view in plain Python (`tests/ui/test_presenters.py`).
* A handful of `pytest-qt` tests drive the real window to check the wiring.
* The window code is long but flat: layout and signal connections only.
