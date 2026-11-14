# 2. Ports and adapters around a standard-library core

Date: 2026-11-14 · Status: accepted

## Context

The value of the program is its arithmetic. The window, the file formats and the
plotting library will change long before the physics does, and the arithmetic must be
testable in milliseconds, without a display.

## Decision

Four layers, dependencies pointing inwards only:

* `domain` - the calculation: immutable values and pure functions, standard library
  only (no NumPy, no Qt);
* `application` - the use cases and the ports (`typing.Protocol`) they need: read
  reflections, render a report, render a table, store text;
* `adapters` and `ui` - implementations of those ports, and the window;
* `main` - the composition root, the only module that knows every concrete class.

The rule is a test: `import-linter` contracts in `pyproject.toml`, run by
`tests/architecture/test_layers.py` and in CI, plus an independent AST check of the
domain's imports.

## Consequences

* A new input format or report layout is one adapter; no use case changes.
* The domain's 150-odd tests run in about five seconds.
* NumPy is used only by the plot; the fit is a dozen lines of `math.fsum`, which is
  enough for ten reflections and keeps the core dependency-free.
