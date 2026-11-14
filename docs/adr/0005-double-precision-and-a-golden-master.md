# 5. Double precision, checked against the full program

Date: 2026-11-14 · Status: accepted

## Context

The full SizeOut program reproduces a QuickBASIC original byte for byte, single-precision
rounding included. The demo was written from scratch and has no such obligation, but its
numbers must be right - and "right" needs an independent witness.

## Decision

* The demo computes in double precision.
* `tools/make_golden.py` runs the same inputs through the full program and records the
  results in `tests/golden/full_program_reference.json` (the full program itself is not
  part of this repository). `tests/domain/test_golden.py` compares within 3 parts in
  10⁷ - the precision of single-precision storage.
* Three further layers do not depend on the full program at all: worked examples
  computed by hand, property tests (`hypothesis`) and a mutation check
  (`tools/mutation_check.py`) that plants known bugs and requires the suite to fail.

## Consequences

* The fit coefficients agree to 12 digits (both programs fit in double); D, e, the
  densities and the calculator agree to 7.
* The golden file pins the sample by SHA-256, so a regenerated sample cannot silently
  invalidate the reference.
* Where the demo deliberately differs from the full program, the test says so by name
  (see ADR 6).
