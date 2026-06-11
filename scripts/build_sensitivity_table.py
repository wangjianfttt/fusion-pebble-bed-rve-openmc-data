#!/usr/bin/env python3
"""Build LaTeX table for PF=0.618 sensitivity results from CSV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results/pairwise_shifts.csv"
OUT = ROOT / "tables/tex/pf618_sensitivity_summary.tex"


def fmt(value: float, sigma: float) -> str:
    return f"${value:+.2f}\\pm{sigma:.2f}$"


def main() -> int:
    df = pd.read_csv(IN)
    labels = {
        "pf618_vacuum": "Axial vacuum, neutron mode",
        "pf618_endfb80_vacuum": "Axial vacuum, ENDF/B-VIII.0",
        "pf618_fendl32c_vacuum": "Axial vacuum, FENDL-3.2c",
        "pf618_zreflective": "All-reflective, neutron mode",
        "pf618_photon_vacuum": "Axial vacuum, photon transport",
    }
    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\caption{PF=0.618 sensitivity summary for paired homogenised and geometry-resolved RVE calculations.  All values are resolved--homogenised relative shifts, $(B/A-1)\times100$ \%, with propagated one-standard-deviation (1$\sigma$) statistical uncertainty.  TPR$_6$ is the local $^6$Li(n,t) tritium-production response per source neutron.  The axial-vacuum ENDF/B-VII.1, ENDF/B-VIII.0, FENDL-3.2c and photon-transport rows used 80 fixed-source batches with 30000 particles per batch.  The all-reflective case used 10 fixed-source batches with 5000 particles per batch because the absence of axial leakage substantially lengthened resolved-geometry particle histories.  The photon-transport row is used for heating-score interpretation; its unfiltered flux tally contains both neutron and photon track-length contributions and is not interpreted as neutron flux.}",
        r"\label{tab:pf618_sensitivity}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2pt}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{>{\raggedright\arraybackslash}p{3.0cm}ccccc}",
        r"\toprule",
        r"\textbf{Case} & \textbf{TPR$_6$} & \textbf{H3 production} & \textbf{$^9$Be(n,2n)} & \textbf{Heating} & \textbf{Flux} \\",
        r"\midrule",
    ]
    for pair_id in ["pf618_vacuum", "pf618_endfb80_vacuum", "pf618_fendl32c_vacuum", "pf618_zreflective", "pf618_photon_vacuum"]:
        row = df[df["pair_id"] == pair_id].iloc[0]
        flux = fmt(row["flux_total_shift_pct"], row["flux_total_shift_pct_1sigma"])
        if pair_id == "pf618_photon_vacuum":
            flux += r"$^{a}$"
        lines.append(
            f"{labels[pair_id]} & "
            f"{fmt(row['tpr6_shift_pct'], row['tpr6_shift_pct_1sigma'])} & "
            f"{fmt(row['h3_production_total_shift_pct'], row['h3_production_total_shift_pct_1sigma'])} & "
            f"{fmt(row['be_n2n_rate_shift_pct'], row['be_n2n_rate_shift_pct_1sigma'])} & "
            f"{fmt(row['heating_total_shift_pct'], row['heating_total_shift_pct_1sigma'])} & "
            f"{flux} \\\\"
        )
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"}",
        r"\begin{flushleft}",
        r"\footnotesize $^{a}$Unfiltered OpenMC flux with photon transport enabled includes neutron and photon contributions; this value is retained in the source CSV but is not used as a neutron-flux metric.",
        r"\end{flushleft}",
        r"\end{table}",
        "",
    ])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
