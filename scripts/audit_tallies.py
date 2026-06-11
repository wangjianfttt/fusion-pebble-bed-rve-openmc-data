#!/usr/bin/env python3
"""Audit OpenMC tally values, units, and propagated uncertainties.

The script prefers OpenMC statepoint files and reconstructs tally means and
standard deviations from the cumulative statepoint datasets.  It does not
require the OpenMC Python package; h5py is sufficient for the statepoints
included with this repository.  If a statepoint is unavailable, the script can
fall back to a case-level ``tallies.csv`` file and records that provenance.

Outputs
-------
results/audit/global_tallies_checked.csv
results/audit/global_tallies_checked.tex
results/audit/uncertainty_check.md
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import h5py
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "openmc_results"
OUT = ROOT / "results" / "audit"
MANUSCRIPT = ROOT / "manuscript" / "paper_final_en.tex"

CASE_ORDER = [
    "case_A_homogenized",
    "case_B_resolved_initial",
    "case_C_thermal_expansion_0p5",
    "case_D_thermal_expansion_1p0",
    "case_E_uniform_swelling_1p0",
    "case_F_uniform_swelling_2p0",
    "case_G_flux_driven_swelling",
    "case_H_feedback_iteration",
]

CASE_LABEL = {
    "case_A_homogenized": "A",
    "case_B_resolved_initial": "B",
    "case_C_thermal_expansion_0p5": "C",
    "case_D_thermal_expansion_1p0": "D",
    "case_E_uniform_swelling_1p0": "E",
    "case_F_uniform_swelling_2p0": "F",
    "case_G_flux_driven_swelling": "G",
    "case_H_feedback_iteration": "H",
}

TALLY_MAP = {
    "TBR_global": {
        "quantity": "TPR6, local 6Li(n,t) tritium-production response",
        "csv_mean": "tbr_mean",
        "csv_std": "tbr_std",
        "native_units": "reactions/source",
        "report_units": "reactions/source",
        "scale": 1.0,
    },
    "Be_n2n": {
        "quantity": "9Be(n,2n)",
        "csv_mean": "be_n2n_rate_mean",
        "csv_std": "be_n2n_rate_std",
        "native_units": "reactions/source",
        "report_units": "reactions/source",
        "scale": 1.0,
    },
    "heating_total": {
        "quantity": "Heating",
        "csv_mean": "heating_total_mean",
        "csv_std": "heating_total_std",
        "native_units": "eV/source",
        "report_units": "MeV/source",
        "scale": 1.0e-6,
    },
    "flux_total": {
        "quantity": "Flux",
        "csv_mean": "flux_total_mean",
        "csv_std": "flux_total_std",
        "native_units": "track-length flux tally, particle-cm/source",
        "report_units": "track-length flux tally, particle-cm/source",
        "scale": 1.0,
    },
    "TBR_breeder": {
        "quantity": "Legacy all-nuclide (n,t), not total H3-production",
        "csv_mean": "tbr_breeder_only_mean",
        "csv_std": "tbr_breeder_only_std",
        "native_units": "reactions/source",
        "report_units": "reactions/source",
        "scale": 1.0,
    },
    "dpa_total": {
        "quantity": "Damage energy",
        "csv_mean": None,
        "csv_std": None,
        "native_units": "eV/source",
        "report_units": "eV/source",
        "scale": 1.0,
    },
    "TBR_mesh": {
        "quantity": "Mesh TPR6, local 6Li(n,t) response",
        "csv_mean": None,
        "csv_std": None,
        "native_units": "reactions/source per mesh bin",
        "report_units": "reactions/source per mesh bin",
        "scale": 1.0,
    },
    "H3_production_total": {
        "quantity": "Total H3-production",
        "csv_mean": "h3_production_total_mean",
        "csv_std": "h3_production_total_std",
        "native_units": "tritons/source",
        "report_units": "tritons/source",
        "scale": 1.0,
    },
    "H3_production_Li6": {
        "quantity": "Li6 H3-production",
        "csv_mean": "h3_production_li6_mean",
        "csv_std": "h3_production_li6_std",
        "native_units": "tritons/source",
        "report_units": "tritons/source",
        "scale": 1.0,
    },
    "H3_production_Li7": {
        "quantity": "Li7 H3-production",
        "csv_mean": "h3_production_li7_mean",
        "csv_std": "h3_production_li7_std",
        "native_units": "tritons/source",
        "report_units": "tritons/source",
        "scale": 1.0,
    },
    "H3_production_breeder": {
        "quantity": "Breeder-material H3-production",
        "csv_mean": "h3_production_breeder_mean",
        "csv_std": "h3_production_breeder_std",
        "native_units": "tritons/source",
        "report_units": "tritons/source",
        "scale": 1.0,
    },
    "H3_production_mesh": {
        "quantity": "Mesh H3-production",
        "csv_mean": None,
        "csv_std": None,
        "native_units": "tritons/source per mesh bin",
        "report_units": "tritons/source per mesh bin",
        "scale": 1.0,
    },
    "heating_mesh": {
        "quantity": "Mesh heating",
        "csv_mean": None,
        "csv_std": None,
        "native_units": "eV/source per mesh bin",
        "report_units": "MeV/source per mesh bin",
        "scale": 1.0e-6,
    },
    "flux_mesh": {
        "quantity": "Mesh flux",
        "csv_mean": None,
        "csv_std": None,
        "native_units": "track-length flux tally, particle-cm/source per mesh bin",
        "report_units": "track-length flux tally, particle-cm/source per mesh bin",
        "scale": 1.0,
    },
    "n2n_mesh": {
        "quantity": "Mesh 9Be(n,2n)",
        "csv_mean": None,
        "csv_std": None,
        "native_units": "reactions/source per mesh bin",
        "report_units": "reactions/source per mesh bin",
        "scale": 1.0,
    },
    "dpa_mesh": {
        "quantity": "Mesh damage energy",
        "csv_mean": None,
        "csv_std": None,
        "native_units": "eV/source per mesh bin",
        "report_units": "eV/source per mesh bin",
        "scale": 1.0,
    },
}

MESH_TALLIES = {"TBR_mesh", "H3_production_mesh", "heating_mesh", "flux_mesh", "n2n_mesh", "dpa_mesh"}


@dataclass
class RunMeta:
    run_mode: str = ""
    batches: int | None = None
    inactive: int | None = None
    particles: int | None = None
    photon_transport: str = "not enabled in settings.xml"
    cross_sections: str = "not recorded in XML"


def decode(value):
    if hasattr(value, "decode"):
        return value.decode()
    return value


def h5_string(ds) -> str:
    value = ds[()]
    if hasattr(value, "decode"):
        return value.decode()
    return str(value)


def h5_string_array(ds) -> str:
    value = ds[()]
    if getattr(value, "dtype", None) is not None and value.dtype.kind == "S":
        return ";".join(x.decode() for x in value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return ";".join(str(x) for x in value)
    return str(value)


def statepoint_for_case(case_dir: Path) -> Path | None:
    preferred = [
        case_dir / "statepoint.h5",
        case_dir / "statepoint.200.h5",
    ]
    if case_dir.name == "case_H_feedback_iteration":
        preferred = [
            case_dir / "iteration_2" / "statepoint.h5",
            case_dir / "iteration_2" / "statepoint.200.h5",
            case_dir / "statepoint_iter2.h5",
            case_dir / "statepoint.h5",
        ]
    for path in preferred:
        if path.exists():
            return path
    candidates = sorted(case_dir.glob("statepoint*.h5"))
    return candidates[-1] if candidates else None


def read_settings_xml(case_dir: Path) -> RunMeta:
    meta = RunMeta()
    path = case_dir / "settings.xml"
    if not path.exists():
        return meta
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return meta

    def find_text(tag: str) -> str | None:
        node = root.find(f".//{{*}}{tag}")
        return node.text.strip() if node is not None and node.text else None

    for attr, tag in [("batches", "batches"), ("inactive", "inactive"), ("particles", "particles")]:
        text = find_text(tag)
        if text:
            try:
                setattr(meta, attr, int(float(text)))
            except ValueError:
                pass
    photon = find_text("photon_transport")
    if photon:
        meta.photon_transport = photon
    return meta


def read_materials_xml(case_dir: Path, meta: RunMeta) -> RunMeta:
    path = case_dir / "materials.xml"
    if not path.exists():
        return meta
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'cross_sections="([^"]+)"', text)
    if match:
        meta.cross_sections = match.group(1)
    return meta


def mean_std_from_statepoint(sp_path: Path, case: str, meta: RunMeta) -> list[dict]:
    rows: list[dict] = []
    with h5py.File(sp_path, "r") as h5:
        if "run_mode" in h5:
            meta.run_mode = h5_string(h5["run_mode"])
        state_n = int(h5["n_realizations"][()]) if "n_realizations" in h5 else None
        tally_group = h5["tallies"]
        ids = tally_group.attrs.get("ids", [])
        for tid in ids:
            g = tally_group[f"tally {int(tid)}"]
            name = h5_string(g["name"])
            scores = h5_string_array(g["score_bins"])
            nuclides = h5_string_array(g["nuclides"])
            filters = ""
            if "filters" in g:
                filters = ";".join(str(int(x)) for x in g["filters"][()])
            n_real = int(g["n_realizations"][()]) if "n_realizations" in g else state_n
            if not n_real:
                continue
            arr = g["results"][()]
            flat = arr.reshape(-1, 2)
            sums = flat[:, 0]
            sums_sq = flat[:, 1]
            means = sums / n_real
            variances = (sums_sq / n_real - means**2) / max(n_real - 1, 1)
            stds = variances.clip(min=0) ** 0.5
            if name in MESH_TALLIES:
                mean = float(means.sum())
                std = float((stds**2).sum() ** 0.5)
                bin_count = len(means)
            else:
                mean = float(means[0])
                std = float(stds[0])
                bin_count = 1
            info = TALLY_MAP.get(name, {})
            scale = float(info.get("scale", 1.0))
            rows.append(
                {
                    "case": case,
                    "case_label": CASE_LABEL.get(case, case),
                    "statepoint": str(sp_path.relative_to(ROOT)),
                    "source": "statepoint",
                    "tally_id": int(tid),
                    "tally_name": name,
                    "quantity": info.get("quantity", name),
                    "score": scores,
                    "nuclides": nuclides,
                    "filters": "none" if not filters else f"filter_id={filters}",
                    "bin_count": bin_count,
                    "mean_native": mean,
                    "std_native": std,
                    "native_units": info.get("native_units", "OpenMC native score units/source"),
                    "mean_report": mean * scale,
                    "std_report": std * scale,
                    "report_units": info.get("report_units", "OpenMC native score units/source"),
                    "n_realizations": n_real,
                    "run_mode": meta.run_mode,
                    "batches": meta.batches,
                    "inactive": meta.inactive,
                    "particles": meta.particles,
                    "photon_transport": meta.photon_transport,
                    "cross_sections": meta.cross_sections,
                }
            )
    return rows


def rows_from_csv(case_dir: Path, case: str, meta: RunMeta) -> list[dict]:
    path = case_dir / "tallies.csv"
    if not path.exists():
        return []
    data = pd.read_csv(path).iloc[0]
    rows = []
    for tally_name, info in TALLY_MAP.items():
        mean_col = info.get("csv_mean")
        std_col = info.get("csv_std")
        if not mean_col or mean_col not in data:
            continue
        mean = float(data[mean_col])
        std = float(data[std_col]) if std_col in data else float("nan")
        scale = float(info.get("scale", 1.0))
        rows.append(
            {
                "case": case,
                "case_label": CASE_LABEL.get(case, case),
                "statepoint": "",
                "source": str(path.relative_to(ROOT)),
                "tally_id": "",
                "tally_name": tally_name,
                "quantity": info["quantity"],
                "score": score_for_tally(tally_name),
                "nuclides": nuclides_for_tally(tally_name),
                "filters": "none",
                "bin_count": 1,
                "mean_native": mean,
                "std_native": std,
                "native_units": info["native_units"],
                "mean_report": mean * scale,
                "std_report": std * scale,
                "report_units": info["report_units"],
                "n_realizations": "",
                "run_mode": meta.run_mode,
                "batches": meta.batches,
                "inactive": meta.inactive,
                "particles": meta.particles,
                "photon_transport": meta.photon_transport,
                "cross_sections": meta.cross_sections,
            }
        )
    return rows


def score_for_tally(name: str) -> str:
    return {
        "TBR_global": "(n,t)",
        "H3_production_total": "H3-production",
        "H3_production_Li6": "H3-production",
        "H3_production_Li7": "H3-production",
        "H3_production_breeder": "H3-production",
        "H3_production_mesh": "H3-production",
        "Be_n2n": "(n,2n)",
        "heating_total": "heating",
        "flux_total": "flux",
        "TBR_breeder": "(n,t)",
        "dpa_total": "damage-energy",
    }.get(name, "")


def nuclides_for_tally(name: str) -> str:
    return {
        "TBR_global": "Li6",
        "H3_production_Li6": "Li6",
        "H3_production_Li7": "Li7",
        "H3_production_breeder": "total",
        "Be_n2n": "Be9",
        "heating_total": "total",
        "flux_total": "total",
        "TBR_breeder": "total",
        "dpa_total": "total",
    }.get(name, "")


def all_case_dirs() -> list[Path]:
    dirs = [RESULTS / c for c in CASE_ORDER if (RESULTS / c).exists()]
    mech = sorted((RESULTS / "mechanism_study").glob("mech_*")) if (RESULTS / "mechanism_study").exists() else []
    return dirs + [d for d in mech if d.is_dir()]


def audit_cases() -> pd.DataFrame:
    rows: list[dict] = []
    for case_dir in all_case_dirs():
        case = case_dir.name
        meta = read_settings_xml(case_dir)
        meta = read_materials_xml(case_dir, meta)
        sp = statepoint_for_case(case_dir)
        if sp is not None:
            try:
                rows.extend(mean_std_from_statepoint(sp, case, meta))
                continue
            except Exception as exc:
                print(f"warning: failed to read {sp}: {exc}", file=sys.stderr)
        rows.extend(rows_from_csv(case_dir, case, meta))
    return pd.DataFrame(rows)


def scalar(df: pd.DataFrame, case: str, tally: str) -> tuple[float, float]:
    match = df[(df.case == case) & (df.tally_name == tally) & (df.filters == "none")]
    if match.empty:
        raise KeyError(f"missing {case} {tally}")
    row = match.iloc[0]
    return float(row.mean_report), float(row.std_report)


def delta(a: float, sa: float, b: float, sb: float) -> tuple[float, float, float]:
    ratio = b / a
    sigma_ratio = ratio * math.sqrt((sa / a) ** 2 + (sb / b) ** 2)
    return (ratio - 1.0) * 100.0, sigma_ratio * 100.0, ratio


def fmt_sci(value: float, sigma: float, power: int, digits: int = 3) -> str:
    scale = 10.0**power
    return f"$({value/scale:.{digits}f}\\pm{sigma/scale:.{digits}f})\\times10^{{{power}}}$"


def make_ab_table(df: pd.DataFrame) -> str:
    specs = [
        ("TPR$_6$ ($^6$Li(n,t))", "TBR_global", -4, 3),
        ("$^9$Be(n,2n)", "Be_n2n", -2, 4),
        ("Heating", "heating_total", -1, 4),
        ("Flux", "flux_total", 0, 4),
    ]
    lines = [
        "\\begin{tabular}{lccc}",
        "\\toprule",
        "\\textbf{Quantity} & \\textbf{Homogenised (A)} & \\textbf{Resolved (B)} & \\textbf{$\\Delta$ (\\%)} \\\\",
        "\\midrule",
    ]
    for label, tally, power, digits in specs:
        a, sa = scalar(df, "case_A_homogenized", tally)
        b, sb = scalar(df, "case_B_resolved_initial", tally)
        d, sd, _ = delta(a, sa, b, sb)
        if tally == "flux_total":
            aval = f"${a:.4f}\\pm{sa:.4f}$"
            bval = f"${b:.4f}\\pm{sb:.4f}$"
        else:
            aval = fmt_sci(a, sa, power, digits)
            bval = fmt_sci(b, sb, power, digits)
        lines.append(f"{label} & {aval} & {bval} & $\\mathbf{{{d:+.2f}\\pm{sd:.2f}}}$ \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    return "\n".join(lines)


def manuscript_checks(df: pd.DataFrame) -> list[str]:
    text = MANUSCRIPT.read_text(encoding="utf-8", errors="ignore") if MANUSCRIPT.exists() else ""
    lines = []
    lines.append("# Tally uncertainty and unit audit")
    lines.append("")
    lines.append("## Data sources")
    statepoint_rows = int((df["source"] == "statepoint").sum())
    csv_rows = int((df["source"] != "statepoint").sum())
    lines.append(f"- Tally rows read from statepoint files: {statepoint_rows}")
    lines.append(f"- Tally rows read from CSV fallback: {csv_rows}")
    lines.append("- OpenMC Python API was not required; statepoint cumulative sums were read with h5py and converted to mean/std_dev using `n_realizations`.")
    h_case = "case_H_feedback_iteration"
    h_rows = df[(df.case == h_case) & (df.tally_name == "TBR_global") & (df.filters == "none")]
    if not h_rows.empty:
        lines.append(f"- Case H final feedback values were read from `{h_rows.iloc[0].statepoint}`.")
        stale = RESULTS / h_case / "statepoint_iter2.h5"
        if stale.exists() and str(stale.relative_to(ROOT)) != h_rows.iloc[0].statepoint:
            lines.append(f"- WARNING: `{stale.relative_to(ROOT)}` also exists but is not used because it is inconsistent with `iteration_2/statepoint.h5`, `tallies.csv`, and `feedback_summary.csv`.")
    lines.append("")
    lines.append("## OpenMC-native units")
    lines.append("- `(n,t)` and `(n,2n)` reaction scores are reaction rates per source particle for these fixed-source tallies.")
    lines.append("- `TBR_global` is a legacy tally name for the local `6Li(n,t)` tritium-production response (TPR6), not a full-blanket tritium breeding ratio.")
    lines.append("- `TBR_breeder` is an all-nuclide `(n,t)` score when present; it is not equivalent to OpenMC `H3-production` and is not used as total tritium production.")
    lines.append("- `heating` is an OpenMC heating score in eV/source. Manuscript MeV/source values must be multiplied by `1e-6`.")
    lines.append("- `damage-energy` is eV/source unless explicitly converted.")
    lines.append("- `flux` is a track-length flux tally in particle-cm/source for the current unfiltered global tally. The current mesh flux is not volume-normalized unless divided by mesh-cell volume.")
    h3_present = bool(df["tally_name"].astype(str).str.contains("H3_production").any())
    if h3_present:
        lines.append("- Dedicated `H3-production` tallies were found in the audited statepoints and should be reported separately from TPR6.")
    else:
        lines.append("- No dedicated `H3-production` score was found in the audited statepoints; the manuscript values are based on the `TBR_global` `6Li(n,t)` reaction-rate tally and are reported as TPR6.")
    lines.append("")
    lines.append("## A/B propagated differences")
    for tally in ["TBR_global", "Be_n2n", "heating_total", "flux_total"]:
        a, sa = scalar(df, "case_A_homogenized", tally)
        b, sb = scalar(df, "case_B_resolved_initial", tally)
        d, sd, _ = delta(a, sa, b, sb)
        unit = df[(df.case == "case_A_homogenized") & (df.tally_name == tally) & (df.filters == "none")].iloc[0].report_units
        lines.append(f"- {tally}: A = {a:.12g} +/- {sa:.3g} {unit}; B = {b:.12g} +/- {sb:.3g} {unit}; delta = {d:+.6f} +/- {sd:.6f} % (1 sigma).")
    lines.append("")
    lines.append("## Manuscript comparison flags")
    if "Heating (MeV)" in text and "10^{5}" in text:
        lines.append("- FLAG: Table 3 labels heating as MeV while displaying values of order `10^5`. The audited OpenMC score is `heating` in eV/source, corresponding to approximately `0.4233` and `0.3440` MeV/source for Cases A and B.")
    if "total neutron flux (arbitrary normalisation)" in text:
        lines.append("- FLAG: Methods currently describes flux as arbitrary. It should be described as an OpenMC track-length flux tally per source particle, not volume-normalized unless explicitly divided by volume.")
    if "50 inactive batches" in text:
        lines.append("- FLAG: Fixed-source calculations do not require inactive batches for eigenvalue source convergence. The manuscript should state that inactive batches were present in settings but are not physically required for fixed-source source convergence, or rerun/remove them.")
    if "damage-energy" not in text or "eV/source" not in text:
        lines.append("- FLAG: Damage-energy unit statement should be checked.")
    lines.append("")
    lines.append("## Tally definitions found in statepoints")
    defs = df[["tally_name", "score", "nuclides", "filters", "native_units", "report_units"]].drop_duplicates().sort_values(["filters", "tally_name"])
    for _, row in defs.iterrows():
        lines.append(f"- `{row.tally_name}`: score `{row.score}`, nuclides `{row.nuclides}`, filters `{row.filters}`, native units `{row.native_units}`, reported units `{row.report_units}`.")
    return lines


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = audit_cases()
    if df.empty:
        raise SystemExit("No tally data found.")
    df = df.sort_values(["case", "filters", "tally_id", "tally_name"])
    df.to_csv(OUT / "global_tallies_checked.csv", index=False)
    (OUT / "global_tallies_checked.tex").write_text(make_ab_table(df), encoding="utf-8")
    (OUT / "uncertainty_check.md").write_text("\n".join(manuscript_checks(df)) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'global_tallies_checked.csv'}")
    print(f"wrote {OUT / 'global_tallies_checked.tex'}")
    print(f"wrote {OUT / 'uncertainty_check.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
