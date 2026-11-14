# 6. The Lorentz size-strain plot with cos θ

Date: 2026-11-14 · Status: accepted

## Context

For Lorentz profiles the size-strain plot is linear in

$$ y = \frac{d\thinspace \beta\cos\theta}{\lambda} = \frac1D\thinspace (K d) + \frac{K_\varepsilon e}{2}. $$

The full program's fit mode, which places reflections on the plot itself, follows the
convention of the log it was built from and uses $y = d\beta/\lambda$, without
$\cos\theta$. Its back-transform of a line typed in (the program's main use) is
unaffected.

## Decision

The demo uses the exact form above, like the other five linearizations.

## Consequences

* The round-trip property holds for all six plots
  (`test_round_trip_through_every_linearization`); with the other form it fails - the
  mutation check plants exactly that change and it is caught.
* For the bundled sample the two programs disagree on this one fit. The golden test
  records the full program's line but does not compare it, and
  `test_the_lorentz_size_strain_fit_differs_on_purpose` documents the difference.
