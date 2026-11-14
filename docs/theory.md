# The method

How Size-Strain Lab turns the widths of diffraction lines into a crystallite size,
a microstrain and a dislocation density. Every formula on this page is implemented
in `src/sizeout_demo/domain/` and checked by a test named in the last column of the
tables in [architecture.md, section 10](architecture.md#10-quality-requirements).

Symbols: $2\theta$ is the position of a reflection, $\beta$ its width (FWHM) in
radians **after** the instrumental contribution has been removed, $\lambda$ the
wavelength, $d = \lambda / 2\sin\theta$ the interplanar spacing, $D$ the crystallite
size, $e$ the microstrain ($e_s = 100\thinspace e$ in %), $K$ the Scherrer constant (0.94)
and $K_\varepsilon$ the strain constant (4).

## 1. Two kinds of broadening

A small crystallite and a strained lattice both widen a reflection, but they depend
on the angle differently:

$$
\beta_D = \frac{K\lambda}{D\cos\theta} \qquad\text{(Scherrer)}
\qquad\qquad
\beta_\varepsilon = K_\varepsilon\thinspace  e \tan\theta \qquad\text{(Stokes and Wilson)}
$$

How the two add up depends on the shape of the profile:

| Profile | Total width |
|---|---|
| Lorentz | $\beta = \beta_D + \beta_\varepsilon$ |
| Gauss | $\beta^2 = \beta_D^2 + \beta_\varepsilon^2$ |
| pseudo-Voigt | $\beta = \beta_D + \beta_\varepsilon^2/\beta$, that is $\beta = \tfrac12\left(\beta_D + \sqrt{\beta_D^2 + 4\beta_\varepsilon^2}\right)$ |

## 2. Six straight lines

Each technique rearranges the sum so that it becomes $y = A + Bx$, with $D$ in one
coefficient and $e$ in the other. Measuring several reflections and fitting the line
separates the two effects.

**Williamson-Hall plot (WHP)** - $D$ from the intercept $A$, $e$ from the slope $B$:

| Profile | $x$ | $y$ | $D$ | $e$ |
|---|---|---|---|---|
| Lorentz | $K_\varepsilon\sin\theta$ | $\beta\cos\theta$ | $K\lambda/A$ | $B$ |
| Gauss | $(K_\varepsilon\sin\theta)^2$ | $(\beta\cos\theta)^2$ | $K\lambda/\sqrt{A}$ | $\sqrt{B}$ |
| pseudo-Voigt | $(K_\varepsilon\sin\theta)^2/(\beta\cos\theta)$ | $\beta\cos\theta$ | $K\lambda/A$ | $\sqrt{B}$ |

**Size-strain plot (SSP)** - $D$ from the slope $B$, $e$ from the intercept $A$
($d$ and $\lambda$ in nm):

| Profile | $x$ | $y$ | $D$ | $e$ |
|---|---|---|---|---|
| Lorentz | $K d$ | $d\beta\cos\theta/\lambda$ | $1/B$ | $2A/K_\varepsilon$ |
| Gauss | $(K d)^2$ | $(d\beta\cos\theta/\lambda)^2$ | $1/\sqrt{B}$ | $2\sqrt{A}/K_\varepsilon$ |
| pseudo-Voigt | $K d^2\beta\cos\theta/\lambda$ | $(d\beta\cos\theta/\lambda)^2$ | $1/B$ | $2\sqrt{A}/K_\varepsilon$ |

Each row is exact: widths made from a known $D$ and $e$ with the matching profile lie
on a straight line, and the fit returns that $D$ and $e$. The property test
`test_round_trip_through_every_linearization` checks it for random sizes, strains,
angles and wavelengths.

## 3. The fit and its uncertainties

Ordinary least squares through the reflections in use:

$$
B = \frac{S_{xy}}{S_{xx}},\quad A = \bar y - B\bar x,\quad
s^2 = \frac{SS_{res}}{n-2},\quad
\sigma_B = \sqrt{\frac{s^2}{S_{xx}}},\quad
\sigma_A = \sqrt{s^2\left(\frac1n + \frac{\bar x^2}{S_{xx}}\right)}
$$

and $R^2 = 1 - SS_{res}/SS_{tot}$. The e.s.d.'s of $D$ and $e$ follow by first-order
propagation, e.g. $\sigma_D = D\thinspace \sigma_A/A$ for $D = K\lambda/A$ and
$\sigma_D = D\thinspace \sigma_A/2A$ for $D = K\lambda/\sqrt{A}$.

Two reflections give a line but no scatter; their own e.s.d.'s are propagated
instead:

$$
\sigma_B = |B|\sqrt{\left(\frac{\sigma_{\Delta x}}{\Delta x}\right)^2 + \left(\frac{\sigma_{\Delta y}}{\Delta y}\right)^2},
\qquad
\sigma_A = \sqrt{\sigma_{y_1}^2 + (x_1\sigma_B)^2 + (B\sigma_{x_1})^2}.
$$

## 4. When a coefficient is not positive

A coefficient $\le 0$ is not an error: it says that one broadening is absent.

* **No strain** (the strain coefficient $\le 0$): $e = 0$, and $D$ is taken from a
  model fitted under that assumption - the Scherrer and / or the Monshi-Scherrer
  model. Two models entered give two solutions.
* **No size broadening** (the size coefficient $\le 0$): the crystallites are
  "infinite", and $e$ comes from the Stokes-Wilson model for $D = \infty$.
* **Neither**: $D = \infty$ and $e = 0$.

## 5. Dislocation density

After Williamson and Smallman (1956), in $\mathrm{cm^{-2}}$ with $D$ and $b$ in nm and
$e_s$ in %:

$$
\rho_D = 10^{14}\thinspace \frac{C\thinspace n}{D^2},
\qquad
\rho_\varepsilon = 10^{10}\thinspace \frac{k}{n}\left(\frac{e_s}{b}\right)^2,
\qquad
\rho = \sqrt{\rho_D\thinspace \rho_\varepsilon} = C_f\thinspace \frac{e_s}{b\thinspace D}\cdot 10^{12},
\quad C_f = \sqrt{k\thinspace C}
$$

$n$ - dislocations at the crystallite boundary, $C$ - 1 for an isotropic and 3 for an
anisotropic distribution, $k$ - between $6/\pi$ (Gauss) and 24 (Cauchy) depending on
the strain distribution, $b$ - the Burgers vector, typed in or $b = \frac{a}{m}\sqrt{u^2+v^2+w^2}$
for a cubic cell. The additive model of Ashby (1970) is given beside it:
$\rho_{total} = \rho_{GND} + \rho_{SSD} = \rho_D + \rho_\varepsilon$, its e.s.d. in
quadrature.

Optionally $D$, $e_s$ and $b$ are first rounded as they would be published (section 7),
so that the densities match the values in the paper.

## 6. The calculator

For one reflection the same equations run forwards and backwards:

* from $D$ and / or $e_s$: $\beta_D$, $\beta_\varepsilon$ and the total width;
* from $\beta_D$ and / or $\beta_\varepsilon$: $D$, $e_s$ and the total;
* from $\rho_D$ and / or $\rho_\varepsilon$: $D$ (for $e = 0$) and $e_s$ (for
  $D = \infty$), each with its own width - there is no total then.

The e.s.d. of $2\theta$ enters as
$\sigma_{\beta_D}/\beta_D = \sqrt{(\sigma_D/D)^2 + (\delta\theta\tan\theta)^2}$ and
$\sigma_{\beta_\varepsilon}/\beta_\varepsilon = \sqrt{(\sigma_e/e)^2 + (\delta\theta/\cos\theta\sin\theta)^2}$.

## 7. Rounding as published

Decimal, half up, on the value as written:

* $D$: whole numbers when $\sigma_D \ge 1$, otherwise $\sigma_D$ to one significant
  digit and $D$ to the same decimal (366.43 ± 0.51 → 366.4 ± 0.5);
* $e_s$: the coarser of two significant digits of $e_s$ and of $\sigma_e$, but
  $\sigma_e$ never rounded away (0.02649 ± 0.0001154 → 0.0265 ± 0.0001);
* $b$: $\sigma_b$ to one significant digit (0.3839943 ± 0.000106 → 0.3840 ± 0.0001).

## References

* G. K. Williamson, W. H. Hall, *Acta Metall.* **1** (1953) 22.
* G. K. Williamson, R. E. Smallman, *Philos. Mag.* **1** (1956) 34.
* M. F. Ashby, *Philos. Mag.* **21** (1970) 399.
* A. Monshi, M. R. Foroughi, M. R. Monshi, *World J. Nano Sci. Eng.* **2** (2012) 154.
* A. A. Levin, SizeCr program package, DOI [10.13140/RG.2.2.15922.89280](https://doi.org/10.13140/RG.2.2.15922.89280).
