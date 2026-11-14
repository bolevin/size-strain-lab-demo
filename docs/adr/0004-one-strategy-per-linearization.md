# 4. One strategy class per technique and profile

Date: 2026-11-14 · Status: accepted

## Context

Two techniques (WHP, SSP) times three profiles (Lorentz, Gauss, pseudo-Voigt) give six
ways to place a reflection on a plot and six ways to read D and e from the line. A
chain of `if technique ... elif profile ...` grows a branch for every new combination
and mixes the two questions.

## Decision

`domain/linearization.py` defines one abstract `Linearization` and six small
subclasses, each answering only "where does a reflection go" (`point`). What the
coefficients mean follows from two tables - the technique decides which coefficient
carries D, the profile whether it enters linearly or squared - shared by all six.
A registry maps `(Technique, Profile)` to the strategy.

## Consequences

* Each plot is ten lines that can be read against [theory.md](../theory.md).
* The round-trip property test iterates over the registry, so a seventh strategy
  would be covered without touching the test.
* The labels of the plot axes live next to the formula they describe.
