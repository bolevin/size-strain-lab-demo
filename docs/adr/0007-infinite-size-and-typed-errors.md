# 7. The infinite crystallite is infinity; missing data is a typed error

Date: 2026-11-14 · Status: accepted

## Context

The full program, like its QuickBASIC original, writes an infinite crystallite as
D = 0 and a value not entered as -1. Both are sentinels a reader has to know, and both
are valid numbers for the arithmetic that follows.

## Decision

* An infinite crystallite is `Quantity(math.inf)`; "not entered" is `None`. The window
  shows ∞ and an empty field.
* Value objects validate themselves on construction (`Quantity`, `Reflection`,
  `Instrument`, `ReferenceModels`, `DislocationSettings`...).
* Errors are types, not strings: `InvalidInput`, `InsufficientData`,
  `ReferenceModelRequired`, all `DomainError`. A missing reference model is reported
  per technique as part of the result, so the other technique still shows its answer.

## Consequences

* `densities()` needs no special case for D = 0: `math.isinf` says what it means.
* Only the golden test knows the old conventions: it maps `0 ↔ inf` and `-1 ↔ None`
  where it compares.
* The presenter catches `DomainError` and `ValueError` (parsing) in one place and shows
  the message; nothing reaches the user as a traceback.
