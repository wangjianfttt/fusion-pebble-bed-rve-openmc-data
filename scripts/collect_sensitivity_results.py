#!/usr/bin/env python3
"""Collect baseline and sensitivity OpenMC outputs into submission CSVs."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


BASELINE_SUMMARY = ROOT / "data/openmc_results/hardsphere_pf_sweep_production/summary.csv"
BASELINE_SHIFTS = ROOT / "data/openmc_results/hardsphere_pf_sweep_production/resolved_vs_homogenized_shifts.csv"
BOUNDARY_DIR = ROOT / "results/sensitivity/pf618_boundary_reflective_10x5k"
PHOTON_DIR = ROOT / "results/sensitivity/pf618_photon_80x30k"
ENDFB80_DIR = ROOT / "results/sensitivity/pf618_endfb80_80x30k"
FENDL32C_DIR = ROOT / "results/sensitivity/pf618_fendl32c_80x30k"
OUT = ROOT / "results"

SENSITIVITY_DIRS = [
    (BOUNDARY_DIR, None),
    (PHOTON_DIR, None),
    (ENDFB80_DIR, "pf618_endfb80_vacuum"),
    (FENDL32C_DIR, "pf618_fendl32c_vacuum"),
]


def select_pf618(df: pd.DataFrame, col: str = "pf_actual") -> pd.DataFrame:
    sub = df[(df[col] - 0.618).abs() < 1e-9].copy()
    if sub.empty:
        raise SystemExit(f"No PF=0.618 rows found using {col}")
    return sub


def baseline_case_summary() -> pd.DataFrame:
    df = select_pf618(pd.read_csv(BASELINE_SUMMARY), "pf_actual")
    rows: list[dict] = []
    for _, row in df.iterrows():
        geom = "homogenised" if row["model"] == "homogenized" else "resolved"
        out = {
            "case_id": f"pf618_vacuum_{geom}",
            "pair_id": "pf618_vacuum",
            "geometry": geom,
            "pf": row["pf_actual"],
            "be_fraction": 0.40,
            "boundary_xy": "reflective",
            "boundary_z": "vacuum",
            "library_label": "ENDFB-7.1-NNDC",
            "cross_sections": "ENDF/B-VII.1 NNDC HDF5; see archived run XML and audit notes",
            "photon_transport": False,
            "batches": 80,
            "particles": 30000,
            "total_histories": 80 * 30000,
            "inactive": 0,
            "seed": 42,
            "openmc_version": "0.15.0",
            "statepoint": f"data/openmc_results/hardsphere_pf_sweep_production/{row['case']}/statepoint.h5",
            "stdout_log": "",
            "stderr_log": "",
            "returncode": 0,
            "lost_particle_status": "not recorded in archived production stdout",
            "started": "",
            "ended": "",
            "min_gap_cm": row.get("min_gap_cm", math.nan),
            "overlap_pairs": row.get("overlap_pairs", math.nan),
            "max_overlap_cm": row.get("max_overlap_cm", math.nan),
        }
        for col in df.columns:
            if col.endswith("_mean") or col.endswith("_std"):
                out[col] = row[col]
        rows.append(out)
    return pd.DataFrame(rows)


def baseline_pairwise() -> pd.DataFrame:
    row = select_pf618(pd.read_csv(BASELINE_SHIFTS), "pf_actual").iloc[0]
    return pd.DataFrame([{
        "pair_id": "pf618_vacuum",
        "homogenised_case": "pf618_vacuum_homogenised",
        "resolved_case": "pf618_vacuum_resolved",
        "pf": row["pf_actual"],
        "boundary_z": "vacuum",
        "library_label": "ENDFB-7.1-NNDC",
        "photon_transport": False,
        "tpr6_shift_pct": row["tpr6_shift_pct"],
        "tpr6_shift_pct_1sigma": row["tpr6_shift_pct_1sigma"],
        "h3_production_total_shift_pct": row["h3_shift_pct"],
        "h3_production_total_shift_pct_1sigma": row["h3_shift_pct_1sigma"],
        "be_n2n_rate_shift_pct": row["be_n2n_shift_pct"],
        "be_n2n_rate_shift_pct_1sigma": row["be_n2n_shift_pct_1sigma"],
        "heating_total_shift_pct": row["heating_shift_pct"],
        "heating_total_shift_pct_1sigma": row["heating_shift_pct_1sigma"],
        "flux_total_shift_pct": row["flux_shift_pct"],
        "flux_total_shift_pct_1sigma": row["flux_shift_pct_1sigma"],
        "flux_note": "neutron-mode track-length flux tally",
    }])


def read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def rename_pair(df: pd.DataFrame, new_pair_id: str | None) -> pd.DataFrame:
    if df.empty or new_pair_id is None:
        return df
    out = df.copy()
    old_pair_ids = sorted(str(x) for x in out["pair_id"].dropna().unique()) if "pair_id" in out else []
    if len(old_pair_ids) != 1:
        raise SystemExit(f"Expected one pair_id before renaming to {new_pair_id}, found {old_pair_ids}")
    old_pair_id = old_pair_ids[0]
    for col in ["pair_id", "homogenised_case", "resolved_case", "case_id"]:
        if col in out:
            out[col] = out[col].astype(str).str.replace(old_pair_id, new_pair_id, regex=False)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    case_frames = [baseline_case_summary()]
    pair_frames = [baseline_pairwise()]
    manifest_frames = [baseline_case_summary()]

    for directory, renamed_pair_id in SENSITIVITY_DIRS:
        case = rename_pair(read_optional_csv(directory / "case_summary.csv"), renamed_pair_id)
        pair = rename_pair(read_optional_csv(directory / "pairwise_shifts.csv"), renamed_pair_id)
        manifest = rename_pair(read_optional_csv(directory / "runs_manifest.csv"), renamed_pair_id)
        if not case.empty:
            case["source_directory"] = str(directory.relative_to(ROOT))
            case_frames.append(case)
        if not manifest.empty:
            manifest["source_directory"] = str(directory.relative_to(ROOT))
            manifest_frames.append(manifest)
        if not pair.empty:
            pair["source_directory"] = str(directory.relative_to(ROOT))
            if "photon" in directory.name:
                pair["flux_note"] = "unfiltered OpenMC flux includes neutron and photon contributions; do not report as neutron flux"
            else:
                pair["flux_note"] = "neutron-mode track-length flux tally"
            pair_frames.append(pair)

    case_summary = pd.concat(case_frames, ignore_index=True, sort=False)
    pairwise = pd.concat(pair_frames, ignore_index=True, sort=False)
    manifest = pd.concat(manifest_frames, ignore_index=True, sort=False)

    case_summary.to_csv(OUT / "case_summary.csv", index=False)
    pairwise.to_csv(OUT / "pairwise_shifts.csv", index=False)
    manifest.to_csv(OUT / "runs_manifest.csv", index=False)

    sw = []
    for directory, _ in SENSITIVITY_DIRS:
        p = directory / "software_versions.txt"
        if p.exists():
            sw.append(f"--- {p.relative_to(ROOT)} ---\n{p.read_text().strip()}\n")
    (OUT / "software_versions.txt").write_text("\n".join(sw))

    libs = []
    for directory, _ in SENSITIVITY_DIRS:
        p = directory / "cross_section_libraries.txt"
        if p.exists():
            libs.append(f"--- {p.relative_to(ROOT)} ---\n{p.read_text().strip()}\n")
    libs.append(
        "ENDFB-8.0-NNDC-minimal was generated from official NNDC ENDF/B-VIII.0 "
        "source files using NJOY2016.68 and OpenMC 0.15.0. The local OpenMC.org "
        "Box HDF5 links returned HTTP 404 on 2026-06-11, so a minimal neutron-only "
        "library was generated for Li6, Li7, Be9, O16, Si28 and He4 at 293.6, 600 "
        "and 900 K. Photon data are not included in this minimal library."
    )
    libs.append(
        "FENDL-3.2c-ACE was generated from the IAEA FENDL-3.2c neutron ACE archive. "
        "The archive was downloaded locally on 2026-06-11, verified with SHA256, "
        "transferred to /data1 on the remote workstation, and converted with "
        "openmc_data 2.4.0 and OpenMC 0.15.0. Remote downloading was not used."
    )
    (OUT / "cross_section_libraries.txt").write_text("\n".join(libs))

    print(f"Wrote {OUT / 'case_summary.csv'}")
    print(f"Wrote {OUT / 'pairwise_shifts.csv'}")
    print(pairwise[[
        "pair_id", "boundary_z", "photon_transport",
        "tpr6_shift_pct", "h3_production_total_shift_pct",
        "be_n2n_rate_shift_pct", "heating_total_shift_pct",
        "flux_total_shift_pct",
    ]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
