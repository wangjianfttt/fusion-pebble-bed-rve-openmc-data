#!/usr/bin/env python3
"""Audit pebble geometry validity and material inventory conservation.

The audit uses archived OpenMC ``model.xml`` sphere definitions when available,
because those are the geometries actually exported to OpenMC. Particle CSV
files are used for material labels and as a fallback geometry source.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "openmc_results"
OUT = ROOT / "results" / "audit"

MAIN_CASES = [
    ("A", "case_A_homogenized", "homogenized reference"),
    ("B", "case_B_resolved_initial", "resolved baseline"),
    ("C", "case_C_thermal_expansion_0p5", "thermal expansion 0.5% linear"),
    ("D", "case_D_thermal_expansion_1p0", "thermal expansion 1.0% linear"),
    ("E", "case_E_uniform_swelling_1p0", "uniform swelling 1 vol.%"),
    ("F", "case_F_uniform_swelling_2p0", "uniform swelling 2 vol.%"),
    ("G", "case_G_flux_driven_swelling", "flux-driven swelling"),
]

FEEDBACK_CASES = [
    ("H0", "case_H_feedback_iteration/iteration_0", "feedback iteration 0"),
    ("H1", "case_H_feedback_iteration/iteration_1", "feedback iteration 1"),
    ("H2", "case_H_feedback_iteration/iteration_2", "feedback iteration 2"),
]

AVOGADRO = 6.02214076e23
MOLAR_MASS = {
    "Li": 6.94,
    "Si": 28.085,
    "O": 15.999,
    "Be": 9.0121831,
    "He": 4.002602,
}


@dataclass
class MaterialConfig:
    rho_breeder: float
    rho_be: float
    rho_he: float
    li6_enrichment: float


def strip(tag: str) -> str:
    return tag.split("}", 1)[-1]


def load_config() -> tuple[dict, MaterialConfig]:
    with (ROOT / "config" / "base_config.yaml").open() as f:
        cfg = yaml.safe_load(f)
    with (ROOT / "config" / "materials.yaml").open() as f:
        mats = yaml.safe_load(f)
    return cfg, MaterialConfig(
        rho_breeder=float(mats["Li4SiO4_breeder"]["density"]),
        rho_be=float(mats["Be_multiplier"]["density"]),
        rho_he=float(mats["void"]["density"]),
        li6_enrichment=float(mats["Li4SiO4_breeder"]["enrichment_Li6"]),
    )


def sphere_volume(r: np.ndarray | float) -> np.ndarray | float:
    return (4.0 / 3.0) * math.pi * np.asarray(r) ** 3


def parse_model_spheres(case_dir: Path) -> pd.DataFrame | None:
    model = case_dir / "model.xml"
    if not model.exists():
        return None
    root = ET.parse(model).getroot()
    rows = []
    for elem in root.iter():
        if strip(elem.tag) != "surface" or elem.attrib.get("type") != "sphere":
            continue
        name = elem.attrib.get("name", "")
        match = re.search(r"pebble_(\d+)", name)
        if not match:
            continue
        coeffs = elem.attrib.get("coeffs", "").split()
        if len(coeffs) != 4:
            continue
        x, y, z, radius = map(float, coeffs)
        rows.append(
            {
                "particle_id": int(match.group(1)),
                "x_model": x,
                "y_model": y,
                "z_model": z,
                "radius_model": radius,
            }
        )
    if not rows:
        return None
    return pd.DataFrame(rows).sort_values("particle_id")


def parse_material_densities(case_dir: Path) -> dict[str, list[float]]:
    model = case_dir / "model.xml"
    densities: dict[str, list[float]] = {"breeder": [], "beryllium": [], "void": []}
    if not model.exists():
        return densities
    root = ET.parse(model).getroot()
    for mat in root.iter():
        if strip(mat.tag) != "material":
            continue
        name = mat.attrib.get("name", "")
        density = None
        for child in mat:
            if strip(child.tag) == "density":
                density = child.attrib.get("value") or child.text
                break
        if density is None:
            continue
        try:
            rho = float(density)
        except ValueError:
            continue
        if "Li4SiO4" in name or "breeder" in name:
            densities["breeder"].append(rho)
        elif "Be_multiplier" in name:
            densities["beryllium"].append(rho)
        elif "void" in name:
            densities["void"].append(rho)
    return densities


def load_particles(case_dir: Path) -> pd.DataFrame | None:
    candidates = [
        case_dir / "particles_iter.csv",
        case_dir / "particles.csv",
        ROOT / "data" / "processed" / "particles.csv",
    ]
    for path in candidates:
        if path.exists():
            df = pd.read_csv(path)
            df.attrs["source_path"] = str(path.relative_to(ROOT))
            return df
    return None


def case_geometry(case_dir: Path) -> tuple[pd.DataFrame, str, str]:
    particles = load_particles(case_dir)
    if particles is None:
        raise FileNotFoundError(f"No particle list found for {case_dir}")
    particles = particles.copy()
    particles["particle_id"] = particles["particle_id"].astype(int)
    model_spheres = parse_model_spheres(case_dir)
    source = particles.attrs.get("source_path", "unknown")
    if model_spheres is not None:
        merged = particles.merge(model_spheres, on="particle_id", how="left")
        for col in ["x", "y", "z", "radius"]:
            merged[f"{col}_csv"] = merged[col]
        merged["x"] = merged["x_model"].fillna(merged["x"])
        merged["y"] = merged["y_model"].fillna(merged["y"])
        merged["z"] = merged["z_model"].fillna(merged["z"])
        merged["radius"] = merged["radius_model"].fillna(merged["radius"])
        return merged, "model.xml spheres with particle labels", source
    return particles, "particle CSV", source


def nearest_gap_stats(df: pd.DataFrame, contact_tol_cm: float = 1e-6) -> dict[str, float | int]:
    pos = df[["x", "y", "z"]].to_numpy(float)
    radii = df["radius"].to_numpy(float)
    n = len(df)
    min_gap = math.inf
    overlap_count = 0
    max_overlap = 0.0
    near_contact = 0
    for i in range(n - 1):
        delta = pos[i + 1 :] - pos[i]
        dist = np.linalg.norm(delta, axis=1)
        gaps = dist - radii[i] - radii[i + 1 :]
        if gaps.size:
            local_min = float(np.min(gaps))
            min_gap = min(min_gap, local_min)
            overlaps = gaps < -contact_tol_cm
            overlap_count += int(np.count_nonzero(overlaps))
            if np.any(overlaps):
                max_overlap = max(max_overlap, float(np.max(-gaps[overlaps])))
            near_contact += int(np.count_nonzero(np.abs(gaps) <= contact_tol_cm))
    return {
        "minimum_gap_cm": min_gap,
        "overlapping_pairs": overlap_count,
        "maximum_overlap_depth_cm": max_overlap,
        "near_contact_pairs_tol_1e-6_cm": near_contact,
        "contact_tolerance_cm": contact_tol_cm,
    }


def material_inventory(
    df: pd.DataFrame,
    cfg: dict,
    mats: MaterialConfig,
    baseline_by_id: pd.DataFrame | None,
    archived_density_mode: str,
) -> dict[str, float]:
    rve_volume = float(cfg["rve_size_x"] * cfg["rve_size_y"] * cfg["rve_size_z"])
    vol = sphere_volume(df["radius"].to_numpy(float))
    df = df.copy()
    df["sphere_volume"] = vol
    breeder = df["type"].astype(int) == 1
    be = df["type"].astype(int) == 2

    if baseline_by_id is not None:
        base = baseline_by_id.set_index("particle_id")["radius"]
        base_r = df["particle_id"].map(base).fillna(df["radius"]).to_numpy(float)
        radius_scale = df["radius"].to_numpy(float) / base_r
        conservative_density_scale = 1.0 / np.maximum(radius_scale, 1e-30) ** 3
    else:
        radius_scale = np.ones(len(df))
        conservative_density_scale = np.ones(len(df))

    if "density_scale" in df.columns:
        density_scale = pd.to_numeric(df["density_scale"], errors="coerce").fillna(1.0).to_numpy(float)
        density_mode = "csv_density_scale"
    elif archived_density_mode == "conservative":
        density_scale = conservative_density_scale
        density_mode = "inferred_conservative"
    else:
        density_scale = np.ones(len(df))
        density_mode = "constant_density_archived"

    mass_breeder = float(np.sum(vol[breeder] * mats.rho_breeder * density_scale[breeder]))
    mass_be = float(np.sum(vol[be] * mats.rho_be * density_scale[be]))
    void_volume = max(rve_volume - float(np.sum(vol)), 0.0)
    mass_he = void_volume * mats.rho_he

    mw_li4sio4 = 4.0 * MOLAR_MASS["Li"] + MOLAR_MASS["Si"] + 4.0 * MOLAR_MASS["O"]
    mol_breeder = mass_breeder / mw_li4sio4
    mol_be = mass_be / MOLAR_MASS["Be"]
    mol_he = mass_he / MOLAR_MASS["He"]

    return {
        "rve_volume_cm3": rve_volume,
        "total_sphere_volume_cm3": float(np.sum(vol)),
        "packing_fraction": float(np.sum(vol) / rve_volume),
        "breeder_sphere_volume_cm3": float(np.sum(vol[breeder])),
        "be_sphere_volume_cm3": float(np.sum(vol[be])),
        "void_volume_cm3": void_volume,
        "n_breeder": int(np.count_nonzero(breeder)),
        "n_be": int(np.count_nonzero(be)),
        "mean_radius_scale_vs_B": float(np.mean(radius_scale)),
        "min_radius_scale_vs_B": float(np.min(radius_scale)),
        "max_radius_scale_vs_B": float(np.max(radius_scale)),
        "density_scale_mode": density_mode,
        "mean_density_scale": float(np.mean(density_scale)),
        "mass_breeder_g": mass_breeder,
        "mass_be_g": mass_be,
        "mass_he_g": mass_he,
        "mass_total_g": mass_breeder + mass_be + mass_he,
        "atoms_Li_total": mol_breeder * 4.0 * AVOGADRO,
        "atoms_Li6": mol_breeder * 4.0 * mats.li6_enrichment * AVOGADRO,
        "atoms_Li7": mol_breeder * 4.0 * (1.0 - mats.li6_enrichment) * AVOGADRO,
        "atoms_Si": mol_breeder * AVOGADRO,
        "atoms_O": mol_breeder * 4.0 * AVOGADRO,
        "atoms_Be": mol_be * AVOGADRO,
        "atoms_He": mol_he * AVOGADRO,
    }


def classify(row: dict[str, object]) -> str:
    if row["case_id"] == "A":
        return "homogenized reference; explicit particle audit is auxiliary"
    if int(row["overlapping_pairs"]) > 0:
        return "invalid_geometry_overlap"
    li_diff = abs(float(row["rel_diff_atoms_Li_total_vs_B_pct"]))
    be_diff = abs(float(row["rel_diff_atoms_Be_vs_B_pct"]))
    if row["case_id"] in {"C", "D", "E", "F", "G", "H1", "H2"} and (li_diff > 0.05 or be_diff > 0.05):
        return "non_conservative_archive_requires_rerun"
    return "geometry_valid_inventory_ok"


def simple_markdown_table(df: pd.DataFrame) -> str:
    """Render a compact Markdown table without optional pandas dependencies."""
    cols = list(df.columns)
    rows = []
    rows.append("| " + " | ".join(cols) + " |")
    rows.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        vals = []
        for col in cols:
            val = row[col]
            if isinstance(val, float):
                vals.append(f"{val:.6g}")
            else:
                vals.append(str(val))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


def main() -> None:
    cfg, mats = load_config()
    cases = MAIN_CASES + FEEDBACK_CASES
    baseline_dir = RESULTS / "case_B_resolved_initial"
    baseline_df, _, _ = case_geometry(baseline_dir)
    baseline_df = baseline_df[["particle_id", "radius"]].copy()

    rows = []
    for case_id, rel_dir, desc in cases:
        case_dir = RESULTS / rel_dir
        df, geom_source, particle_source = case_geometry(case_dir)
        densities = parse_material_densities(case_dir)
        unique_breeder_densities = sorted(set(round(v, 12) for v in densities["breeder"]))
        unique_be_densities = sorted(set(round(v, 12) for v in densities["beryllium"]))
        archived_density_mode = "conservative" if (
            len(unique_breeder_densities) > 1 or len(unique_be_densities) > 1
        ) else "constant"
        inv = material_inventory(df, cfg, mats, baseline_df, archived_density_mode)
        gaps = nearest_gap_stats(df)
        row = {
            "case_id": case_id,
            "case_dir": rel_dir,
            "description": desc,
            "geometry_source": geom_source,
            "particle_source": particle_source,
            "archived_breeder_density_count": len(unique_breeder_densities),
            "archived_be_density_count": len(unique_be_densities),
            "openmc_geometry_debug_status": "not_run_openmc_unavailable_locally",
            "lost_particle_status": "not_verified_no_complete_stdout_archived",
            **inv,
            **gaps,
        }
        rows.append(row)

    out = pd.DataFrame(rows)
    baseline = out.loc[out["case_id"] == "B"].iloc[0]
    for col in [
        "atoms_Li_total",
        "atoms_Li6",
        "atoms_Li7",
        "atoms_Si",
        "atoms_O",
        "atoms_Be",
        "atoms_He",
        "mass_breeder_g",
        "mass_be_g",
        "mass_total_g",
    ]:
        denom = float(baseline[col])
        out[f"rel_diff_{col}_vs_B_pct"] = (out[col] / denom - 1.0) * 100.0 if denom else np.nan
    out["validity_status"] = [classify(row) for row in out.to_dict("records")]

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "geometry_inventory_audit.csv"
    md_path = OUT / "geometry_inventory_audit.md"
    out.to_csv(csv_path, index=False)

    lines = [
        "# Geometry and Material-Inventory Audit",
        "",
        "This audit uses archived OpenMC `model.xml` sphere definitions when present and particle CSV labels as the material-label source. Contact/near-contact pairs use a documented tolerance of `1e-6 cm`.",
        "",
        "## Summary",
        "",
    ]
    for _, row in out.iterrows():
        lines.append(
            f"- {row.case_id} ({row.description}): PF={row.packing_fraction:.6f}, "
            f"min_gap={row.minimum_gap_cm:.3e} cm, overlaps={int(row.overlapping_pairs)}, "
            f"max_overlap={row.maximum_overlap_depth_cm:.3e} cm, "
            f"Li inventory diff={row.rel_diff_atoms_Li_total_vs_B_pct:+.3f} %, "
            f"Be inventory diff={row.rel_diff_atoms_Be_vs_B_pct:+.3f} %, "
            f"status=`{row.validity_status}`."
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Archived deformation cases with constant material density and enlarged pebble radii are non-conservative because atom counts scale with the deformed solid volume.",
        "- A physically conservative rerun should scale each pebble material number density by `1/s_i^3` when radius is scaled by `s_i`. Uniform expansion/swelling can use one density-scaled material per phase; nonuniform flux-driven swelling requires per-scale or per-pebble material cloning.",
        "- OpenMC geometry debugging could not be run locally because OpenMC is not installed in this environment. The retained `tallies.out` files do not include complete lost-particle diagnostics, so lost-particle absence remains a rerun check.",
        "",
        "## Audit table",
        "",
        simple_markdown_table(out[
            [
                "case_id",
                "packing_fraction",
                "minimum_gap_cm",
                "overlapping_pairs",
                "maximum_overlap_depth_cm",
                "near_contact_pairs_tol_1e-6_cm",
                "rel_diff_atoms_Li_total_vs_B_pct",
                "rel_diff_atoms_Be_vs_B_pct",
                "density_scale_mode",
                "validity_status",
            ]
        ]),
        "",
    ]
    md_path.write_text("\n".join(lines))
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
