"""Record the reference values the golden-master tests compare against.

    set SIZEOUT_FULL_APP=C:\\path\\to\\sizeout-app
    python tools/make_golden.py

The values come from the full SizeOut program (not part of this repository).  The
demo was written independently of that code base; agreeing with it is the evidence
that the calculation is right.  The JSON this script writes is committed, so the
tests themselves need nothing but the repository.

The full program keeps its numbers in single precision, as the QuickBASIC original
did, so the values carry about seven significant digits.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "src" / "sizeout_demo" / "data" / "sample_reflections.csv"
OUT = ROOT / "tests" / "golden" / "full_program_reference.json"
PROFILES = ("Lor", "Gau", "pV")
TECHNIQUES = ("WHP", "SSP")

# A, dA, B, dB and the reference models: the ordinary case, the author's own example
# (size-str.prn), and every degenerate line the rules of the reference models cover.
LINES = [
    {"name": "both positive", "a": 3.3458e-3, "da": 9.7e-5, "b": 1.37055e-6, "db": 6.8e-8},
    {
        "name": "author's example",
        "a": 8.75663e-4,
        "da": 6.1941e-5,
        "b": 1.095555,
        "db": 7.21402e-9,
    },
    {"name": "SSP-like", "a": 5.3907e-6, "da": 2.18e-7, "b": 2.32895e-2, "db": 3.15e-4},
    {
        "name": "no strain, Scherrer",
        "a": 3.3e-3,
        "da": 1e-4,
        "b": -2e-7,
        "db": 1e-7,
        "scherrer": (44.0, 1.5),
    },
    {
        "name": "no strain, two models",
        "a": 3.3e-3,
        "da": 1e-4,
        "b": -2e-7,
        "db": 1e-7,
        "scherrer": (44.0, 1.5),
        "monshi": (47.5, 2.0),
    },
    {
        "name": "infinite size, Stokes",
        "a": -4e-4,
        "da": 1e-4,
        "b": 1.2e-6,
        "db": 5e-8,
        "stokes": (0.13, 0.01),
    },
    {"name": "neither", "a": -4e-4, "da": 1e-4, "b": -2e-7, "db": 1e-7},
]

DISLOCATIONS = [
    {
        "name": "author's 16.00 table",
        "D": (240.0, 18.0),
        "es": (0.0147487, 0.0026817),
        "n": 1.0,
        "coeff": 3,
        "k": 12.0,
        "b": (0.384, 0.0),
        "round": False,
    },
    {
        "name": "cubic Al, rounded",
        "D": (43.283037, 1.2561948),
        "es": (0.11707067, 0.002923),
        "n": 1.0,
        "coeff": 3,
        "k": 12.0,
        "a": (4.0495, 0.0005),
        "round": True,
    },
    {
        "name": "isotropic, n = 2",
        "D": (120.0, 7.5),
        "es": (0.05, 0.004),
        "n": 2.0,
        "coeff": 1,
        "k": 6.0,
        "b": (0.25, 0.002),
        "round": False,
    },
    {
        "name": "infinite size",
        "D": (0.0, 0.0),
        "es": (0.08, 0.005),
        "n": 1.0,
        "coeff": 3,
        "k": 24.0,
        "b": (0.2863, 0.0),
        "round": False,
    },
]

ESTIMATES = [
    {
        "name": "D and es, pV",
        "group": "micro",
        "first": (45.0, 2.0),
        "second": (0.12, 0.01),
        "tth": (38.4735, 0.01),
        "profile": "pV",
        "round": False,
    },
    {
        "name": "D and es, Gau, rounded",
        "group": "micro",
        "first": (45.27, 1.94),
        "second": (0.1234, 0.0112),
        "tth": (82.4388, 0.02),
        "profile": "Gau",
        "round": True,
    },
    {
        "name": "es only, Lor",
        "group": "micro",
        "first": None,
        "second": (0.2, 0.02),
        "tth": (65.0987, 0.0),
        "profile": "Lor",
        "round": False,
    },
    {
        "name": "widths, pV",
        "group": "widths",
        "first": (0.18, 0.01),
        "second": (0.06, 0.005),
        "tth": (44.7221, 0.01),
        "profile": "pV",
        "round": False,
    },
    {
        "name": "widths, Lor, rounded",
        "group": "widths",
        "first": (0.21, 0.012),
        "second": (0.09, 0.006),
        "tth": (99.0842, 0.0),
        "profile": "Lor",
        "round": True,
    },
    {
        "name": "densities",
        "group": "densities",
        "first": (1.5e11, 1e10),
        "second": (2.0e10, 1e9),
        "tth": (38.4735, 0.01),
        "profile": "pV",
        "round": False,
    },
    {
        "name": "densities, rounded",
        "group": "densities",
        "first": (1.62e11, 7.5e9),
        "second": (2.0e10, 1.0e9),
        "tth": (78.2318, 0.0),
        "profile": "Gau",
        "round": True,
    },
]

ROUNDING = {
    "size": [
        (366.43, 66.51),
        (366.43, 0.51),
        (43.283037, 1.2561948),
        (42.937717, 0.5811),
        (240.0, 18.0),
        (12.3456, 0.0234),
        (0.9612, 0.0461),
    ],
    "strain": [
        (0.02653, 0.01154),
        (0.02649, 0.201154),
        (0.02649, 0.0001154),
        (0.11707067, 0.002923),
        (0.0147487, 0.0026817),
        (1.2345, 0.0),
    ],
    "burgers": [(0.3839943, 1.06066e-4), (0.286343, 3.5355e-5), (0.25, 0.002)],
}


def pair(value: tuple[float, float] | None) -> tuple[float, float]:
    return (-1.0, -1.0) if value is None else value


def main() -> None:
    full_app = os.environ.get("SIZEOUT_FULL_APP")
    if not full_app or not (Path(full_app) / "sizeout_core.py").exists():
        sys.exit("Set SIZEOUT_FULL_APP to the folder of the full SizeOut program.")
    sys.path.insert(0, full_app)
    import sizeout_core as core  # type: ignore[import-not-found]
    from sizeout_report import VERSION  # type: ignore[import-not-found]

    sys.path.insert(0, str(ROOT / "src"))
    from sizeout_demo.adapters import CsvReflectionReader

    data = CsvReflectionReader().read(SAMPLE)
    reflections = [
        core.Reflection(r.two_theta, r.fwhm, use=r.use) for r in data.reflections
    ]

    fits: list[dict[str, Any]] = []
    for technique in TECHNIQUES:
        for profile in PROFILES:
            fit = core.fit_reflections(reflections, technique, profile, 1.540598, 0.94, 4.0)
            res = core.calc_micro(
                core.CalcInputs(
                    coeff_a=fit.a,
                    d_coeff_a=fit.da,
                    coeff_b=fit.b,
                    d_coeff_b=fit.db,
                    technique=technique,
                    profile=profile,
                )
            )
            fits.append(
                {
                    "technique": technique,
                    "profile": profile,
                    "a": fit.a,
                    "da": fit.da,
                    "b": fit.b,
                    "db": fit.db,
                    "r2": fit.r2,
                    "n": fit.n,
                    "fallback": res.fallback,
                    "D": res.dsize,
                    "dD": res.d_dsize,
                    "es": res.strain,
                    "des": res.d_strain,
                }
            )

    lines: list[dict[str, Any]] = []
    for case in LINES:
        for technique in TECHNIQUES:
            for profile in PROFILES:
                d0s, dd0s = pair(case.get("scherrer"))
                d0m, dd0m = pair(case.get("monshi"))
                esi, desi = pair(case.get("stokes"))
                inp = core.CalcInputs(
                    coeff_a=case["a"],
                    d_coeff_a=case["da"],
                    coeff_b=case["b"],
                    d_coeff_b=case["db"],
                    technique=technique,
                    profile=profile,
                    dzero_s=d0s,
                    d_dzero_s=dd0s,
                    dzero_m=d0m,
                    d_dzero_m=dd0m,
                    szero_d=esi,
                    d_szero_d=desi,
                )
                lines.append(
                    {
                        "case": case["name"],
                        "technique": technique,
                        "profile": profile,
                        "input": {k: v for k, v in case.items() if k != "name"},
                        "solutions": [
                            {
                                "D": r.dsize,
                                "dD": r.d_dsize,
                                "es": r.strain,
                                "des": r.d_strain,
                                "fallback": r.fallback,
                                "source": r.d0_source,
                            }
                            for r in core.calc_variants(inp)
                        ],
                    }
                )

    dislocations: list[dict[str, Any]] = []
    for case in DISLOCATIONS:
        if "a" in case:
            dp = core.DislocationInputs(
                n_boundary=case["n"],
                coeff=case["coeff"],
                k=case["k"],
                burgers_mode="cubic",
                a=case["a"][0],
                da=case["a"][1],
                m=2,
                u=1,
                v=-1,
                w=0,
                round_values=case["round"],
            )
        else:
            dp = core.DislocationInputs(
                n_boundary=case["n"],
                coeff=case["coeff"],
                k=case["k"],
                burgers_mode="enter",
                b=case["b"][0],
                db=case["b"][1],
                round_values=case["round"],
            )
        r = core.dislocation_density(dp, *case["D"], *case["es"])
        dislocations.append(
            {
                "case": case["name"],
                "input": {k: v for k, v in case.items() if k != "name"},
                "b": r.b,
                "db": r.db,
                "ldis_d": r.ldis_d,
                "d_ldis_d": r.d_ldis_d,
                "ldis_es": r.ldis_es,
                "d_ldis_es": r.d_ldis_es,
                "ldis": r.ldis,
                "d_ldis": r.d_ldis,
                "ro_total": r.ro_total,
                "d_ro_total": r.d_ro_total,
                "cf": r.cf,
                "distribution": r.distribution,
            }
        )

    estimates: list[dict[str, Any]] = []
    for case in ESTIMATES:
        first, second = pair(case["first"]), pair(case["second"])
        inp = core.CalcInputs(
            mode="estimation",
            profile=case["profile"],
            tth=case["tth"][0],
            d_tth=case["tth"][1],
            est_round=case["round"],
        )
        if case["group"] == "micro":
            inp.micro_d, inp.micro_dd = first
            inp.micro_es, inp.micro_des = second
        elif case["group"] == "widths":
            inp.est_fw_size, inp.est_d_fw_size = first
            inp.est_fw_strain, inp.est_d_fw_strain = second
        else:
            inp.est_ldis_d, inp.est_d_ldis_d = first
            inp.est_ldis_es, inp.est_d_ldis_es = second
            inp.disl = core.DislocationInputs(
                n_boundary=1.0,
                coeff=3,
                k=12.0,
                burgers_mode="cubic",
                a=4.0495,
                da=0.0005,
                m=2,
                u=1,
                v=-1,
                w=0,
            )
        e = core.estimation_result(inp).est
        estimates.append(
            {
                "case": case["name"],
                "input": {k: v for k, v in case.items() if k != "name"},
                "D": e.d,
                "dD": e.dd,
                "es": e.es,
                "des": e.des,
                "size": e.size,
                "d_size": e.d_size,
                "strain": e.strain,
                "d_strain": e.d_strain,
                "corr": e.corr,
                "d_corr": e.d_corr,
                "b": e.used_b,
                "db": e.used_db,
            }
        )

    rounding = {
        "size": [[*p, *core.round_size(*p)[:2]] for p in ROUNDING["size"]],
        "strain": [[*p, *core.round_strain(*p)[:2]] for p in ROUNDING["strain"]],
        "burgers": [[*p, *core.round_burgers(*p)[:2]] for p in ROUNDING["burgers"]],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "reference": f"SizeOut {VERSION} (full program)",
                "note": "Single precision in the full program: about seven significant "
                "digits. "
                "Its fit mode draws the Lorentz size-strain plot without cos(theta) in y, "
                "as the author's log has it; the demo uses the exact linearization, so "
                "that one fit is recorded but not compared (see docs/adr/0006).",
                "sample_sha256": hashlib.sha256(SAMPLE.read_bytes()).hexdigest(),
                "instrument": {"wavelength": 1.540598, "k_size": 0.94, "k_strain": 4.0},
                "fits": fits,
                "lines": lines,
                "dislocations": dislocations,
                "estimates": estimates,
                "rounding": rounding,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
