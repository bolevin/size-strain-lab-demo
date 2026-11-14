# Glossary

| Term | Meaning |
|---|---|
| **Reflection** | One diffraction line, at angle 2θ, with width FWHM. In the code: `Reflection`. |
| **FWHM** | Full width at half maximum of a reflection, in degrees; here always *after* the instrumental contribution has been removed ("FWHM_corr"). |
| **Crystallite size, D** | The size of the coherently scattering domains, nm. Infinite when there is no size broadening. |
| **Microstrain, e / es** | The relative variation of the lattice spacing; `es` is in %. |
| **e.s.d.** | Estimated standard deviation - the uncertainty of a value. In the code: `Quantity.esd`. |
| **WHP** | Williamson-Hall plot: D from the intercept, e from the slope. |
| **SSP** | Size-strain plot: D from the slope, e from the intercept. |
| **Technique** | WHP or SSP. In the code: `Technique`. |
| **Profile** | The shape of a reflection - Lorentz, Gauss or pseudo-Voigt; it decides how the two broadenings add up. In the code: `Profile`. |
| **Linearization** | One technique with one profile: where a reflection lands on the plot and what the coefficients mean. Six of them, one strategy class each. |
| **K, K_size** | The Scherrer constant (0.94 by default). |
| **K_ε, K_strain** | The strain constant of the Stokes-Wilson term (4 by default). |
| **Reference model** | A value fitted elsewhere under an assumption, used when the line says that one broadening is absent: D0 of Scherrer or Monshi (es = 0), es_inf of Stokes-Wilson (D = ∞). |
| **Solution** | D and es (with their sources) and, if asked for, the densities. Two es = 0 models give two solutions. |
| **Ldis_D, ρ_D, Ro_GND** | Dislocation density due to the crystallite size, cm⁻². |
| **Ldis_es, ρ_ε, Ro_SSD** | Dislocation density due to the microstrain, cm⁻². |
| **Ldis** | The total after Williamson and Smallman: the geometric mean of the two. |
| **Ro_total** | The total after Ashby: their sum. |
| **n** | Dislocations at the crystallite boundary. |
| **Coeff, C** | 1 for an isotropic, 3 for an anisotropic distribution of dislocations. |
| **k** | Coefficient of the strain distribution, 6/π (Gauss) to 24 (Cauchy). |
| **b** | The Burgers vector, nm; typed in or a/m [u v w] of a cubic cell. |
| **Published rounding** | D, es and b rounded as they would be printed in a paper, before the densities are computed from them. |
| **Golden master** | Reference numbers recorded from the full SizeOut program; the demo must reproduce them. |
| **Full program** | SizeOut 16.01, the program this demo was written after; not part of this repository. |
