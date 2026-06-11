#!/usr/bin/env python3
"""Run and collect PF=0.618 paired OpenMC sensitivity cases.

The script is intentionally narrow: it uses the audited hard-sphere PF=0.618
particle list and runs matched homogenised/resolved RVE cases for boundary,
nuclear-data or photon-transport sensitivity studies.  Outputs are written as
CSV files suitable for manuscript tables and reviewer traceability.
"""

from __future__ import annotations

import argparse
import math
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

try:
    import openmc
except ModuleNotFoundError as exc:  # pragma: no cover - production dependency
    raise SystemExit("OpenMC Python bindings are required.") from exc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.build_openmc_model import build_model  # noqa: E402
from src.extract_openmc_tallies import extract_mesh_tallies, extract_scalar_tallies  # noqa: E402


@dataclass(frozen=True)
class CaseSpec:
    pair_id: str
    case_id: str
    geometry: str
    boundary_z: str
    library_label: str
    cross_sections: str
    photon_transport: bool

    @property
    def use_homogenized(self) -> bool:
        return self.geometry == "homogenised"


def load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def clean_previous_outputs(case_dir: Path) -> None:
    for pattern in [
        "statepoint.*.h5",
        "statepoint.h5",
        "summary.h5",
        "volume_*.h5",
        "tallies.out",
        "materials.xml",
        "geometry.xml",
        "settings.xml",
        "tallies.xml",
        "plots.xml",
        "model.xml",
    ]:
        for path in case_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def run_openmc_case(spec: CaseSpec, cfg: dict, mat_cfg: dict, particles_csv: Path,
                    meta: dict, output_root: Path, openmc_exec: str, threads: int | None) -> dict:
    case_dir = output_root / spec.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    clean_previous_outputs(case_dir)

    case_cfg = dict(cfg)
    case_cfg.update({
        "rve_size_x": float(meta["rve_size_x"]),
        "rve_size_y": float(meta["rve_size_y"]),
        "rve_size_z": float(meta["rve_size_z"]),
        "packing_fraction": float(meta["packing_fraction"]),
        "target_packing_fraction": float(meta.get("target_packing_fraction", meta["packing_fraction"])),
        "source_type": "planar",
        "boundary_xy": "reflective",
        "boundary_z": spec.boundary_z,
        "photon_transport": spec.photon_transport,
        "max_lost_particles": int(case_cfg.get("max_lost_particles", 100000)),
    })

    openmc.reset_auto_ids()
    openmc.config["cross_sections"] = spec.cross_sections
    model = build_model(case_cfg, mat_cfg, str(particles_csv), use_homogenized=spec.use_homogenized)
    model.materials.cross_sections = spec.cross_sections
    model.export_to_xml(str(case_dir))
    if not spec.use_homogenized:
        shutil.copy2(particles_csv, case_dir / "particles.csv")

    env = os.environ.copy()
    env["OPENMC_CROSS_SECTIONS"] = spec.cross_sections
    cmd = [openmc_exec]
    if threads and threads > 0:
        cmd.extend(["-s", str(threads)])
    started = datetime.now().isoformat(timespec="seconds")
    proc = subprocess.run(
        cmd,
        cwd=case_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    ended = datetime.now().isoformat(timespec="seconds")
    (case_dir / "openmc_stdout.log").write_text(proc.stdout)
    (case_dir / "openmc_stderr.log").write_text(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"OpenMC failed for {spec.case_id} with return code {proc.returncode}; "
            f"see {case_dir / 'openmc_stderr.log'}"
        )

    statepoints = sorted(case_dir.glob("statepoint.*.h5"))
    if not statepoints:
        raise RuntimeError(f"No statepoint produced for {spec.case_id}")
    sp_path = statepoints[-1]
    shutil.copy2(sp_path, case_dir / "statepoint.h5")

    sp = openmc.StatePoint(str(case_dir / "statepoint.h5"))
    scalars = extract_scalar_tallies(sp)
    mesh = extract_mesh_tallies(sp)
    if mesh is not None:
        mesh.to_csv(case_dir / "tallies_mesh.csv", index=False)

    lost_status = "not_found"
    stdout_lower = proc.stdout.lower()
    stderr_lower = proc.stderr.lower()
    if "lost particle" in stdout_lower or "lost particle" in stderr_lower:
        lost_status = "warning_found"
    elif "maximum number of lost particles" not in stdout_lower + stderr_lower:
        lost_status = "no_warning_in_captured_output"

    row = {
        "case_id": spec.case_id,
        "pair_id": spec.pair_id,
        "geometry": spec.geometry,
        "pf": float(meta["packing_fraction"]),
        "be_fraction": float(cfg.get("beryllium_volume_fraction", 0.40)),
        "boundary_xy": "reflective",
        "boundary_z": spec.boundary_z,
        "library_label": spec.library_label,
        "cross_sections": spec.cross_sections,
        "photon_transport": bool(spec.photon_transport),
        "batches": int(case_cfg["openmc_batches"]),
        "particles": int(case_cfg["openmc_particles"]),
        "total_histories": int(case_cfg["openmc_batches"]) * int(case_cfg["openmc_particles"]),
        "inactive": 0,
        "seed": int(case_cfg.get("seed", 42)),
        "openmc_version": openmc.__version__,
        "statepoint": str((case_dir / "statepoint.h5").relative_to(output_root)),
        "stdout_log": str((case_dir / "openmc_stdout.log").relative_to(output_root)),
        "stderr_log": str((case_dir / "openmc_stderr.log").relative_to(output_root)),
        "returncode": proc.returncode,
        "lost_particle_status": lost_status,
        "started": started,
        "ended": ended,
        "min_gap_cm": float(meta.get("min_gap_cm", math.nan)),
        "overlap_pairs": int(meta.get("overlap_pairs", -1)),
        "max_overlap_cm": float(meta.get("max_overlap_cm", math.nan)),
    }
    row.update(scalars)
    pd.DataFrame([row]).to_csv(case_dir / "tallies.csv", index=False)
    return row


def ratio_shift(resolved: pd.Series, homogenized: pd.Series, mean_col: str, std_col: str) -> tuple[float, float]:
    a = float(homogenized[mean_col])
    b = float(resolved[mean_col])
    sa = float(homogenized[std_col])
    sb = float(resolved[std_col])
    ratio = b / a
    sigma_ratio = ratio * math.sqrt((sa / a) ** 2 + (sb / b) ** 2)
    return (ratio - 1.0) * 100.0, sigma_ratio * 100.0


def build_pairwise_shifts(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    metrics = [
        ("tpr6", "tbr_mean", "tbr_std"),
        ("h3_production_total", "h3_production_total_mean", "h3_production_total_std"),
        ("be_n2n_rate", "be_n2n_rate_mean", "be_n2n_rate_std"),
        ("heating_total", "heating_total_mean", "heating_total_std"),
        ("flux_total", "flux_total_mean", "flux_total_std"),
    ]
    for pair_id, group in summary.groupby("pair_id", sort=True):
        if set(group["geometry"]) < {"homogenised", "resolved"}:
            continue
        h = group[group["geometry"] == "homogenised"].iloc[0]
        r = group[group["geometry"] == "resolved"].iloc[0]
        row = {
            "pair_id": pair_id,
            "homogenised_case": h["case_id"],
            "resolved_case": r["case_id"],
            "pf": r["pf"],
            "boundary_z": r["boundary_z"],
            "library_label": r["library_label"],
            "photon_transport": bool(r["photon_transport"]),
        }
        for prefix, mean_col, std_col in metrics:
            if mean_col in group.columns and std_col in group.columns and pd.notna(h.get(mean_col)) and pd.notna(r.get(mean_col)):
                shift, sigma = ratio_shift(r, h, mean_col, std_col)
                row[f"{prefix}_shift_pct"] = shift
                row[f"{prefix}_shift_pct_1sigma"] = sigma
                row[f"{prefix}_homogenised_mean"] = h[mean_col]
                row[f"{prefix}_homogenised_std"] = h[std_col]
                row[f"{prefix}_resolved_mean"] = r[mean_col]
                row[f"{prefix}_resolved_std"] = r[std_col]
        rows.append(row)
    return pd.DataFrame(rows)


def write_environment_reports(output_root: Path, specs: Iterable[CaseSpec], openmc_exec: str) -> None:
    try:
        version_out = subprocess.run([openmc_exec, "--version"], capture_output=True, text=True, check=False).stdout
    except Exception as exc:  # pragma: no cover
        version_out = f"Could not execute {openmc_exec} --version: {exc}\n"
    lines = [
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Host: {platform.node()}",
        f"Platform: {platform.platform()}",
        f"Python: {sys.version.split()[0]}",
        f"OpenMC Python: {openmc.__version__}",
        f"OpenMC executable: {openmc_exec}",
        "",
        version_out.strip(),
        "",
    ]
    (output_root / "software_versions.txt").write_text("\n".join(lines))

    seen: dict[str, str] = {}
    for spec in specs:
        seen[spec.library_label] = spec.cross_sections
    lib_lines = [f"{label}: {path}" for label, path in sorted(seen.items())]
    (output_root / "cross_section_libraries.txt").write_text("\n".join(lib_lines) + "\n")


def specs_from_args(args: argparse.Namespace) -> list[CaseSpec]:
    specs: list[CaseSpec] = []
    base_label = args.library_label
    base_xs = str(Path(args.cross_sections).expanduser())

    if args.case_set in {"baseline", "all"}:
        for geom in ["homogenised", "resolved"]:
            specs.append(CaseSpec("pf618_vacuum", f"pf618_vacuum_{geom}", geom, "vacuum", base_label, base_xs, False))
    if args.case_set in {"boundary", "all"}:
        for geom in ["homogenised", "resolved"]:
            specs.append(CaseSpec("pf618_zreflective", f"pf618_zreflective_{geom}", geom, "reflective", base_label, base_xs, False))
    if args.case_set in {"photon", "all"}:
        for geom in ["homogenised", "resolved"]:
            specs.append(CaseSpec("pf618_photon_vacuum", f"pf618_photon_vacuum_{geom}", geom, "vacuum", base_label, base_xs, True))
    if args.modern_cross_sections:
        modern_label = args.modern_library_label
        modern_xs = str(Path(args.modern_cross_sections).expanduser())
        for geom in ["homogenised", "resolved"]:
            specs.append(CaseSpec("pf618_modernlib_vacuum", f"pf618_modernlib_vacuum_{geom}", geom, "vacuum", modern_label, modern_xs, False))
    return specs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/base_config.yaml")
    ap.add_argument("--materials", default="config/materials.yaml")
    ap.add_argument("--particles", default="data/openmc_results/hardsphere_pf_sweep_production/particle_variants/particles_pf6180.csv")
    ap.add_argument("--particles-meta", default="data/openmc_results/hardsphere_pf_sweep_production/particle_variants/particles_pf6180_meta.yaml")
    ap.add_argument("--output-root", required=True)
    ap.add_argument("--case-set", choices=["baseline", "boundary", "photon", "all"], default="boundary")
    ap.add_argument("--cross-sections", required=True)
    ap.add_argument("--library-label", default="ENDF/B-VII.1")
    ap.add_argument("--modern-cross-sections", default=None)
    ap.add_argument("--modern-library-label", default="modern")
    ap.add_argument("--batches", type=int, default=80)
    ap.add_argument("--particles-per-batch", type=int, default=30000)
    ap.add_argument("--openmc-exec", default=os.environ.get("OPENMC_EXEC", "openmc"))
    ap.add_argument("--threads", type=int, default=None)
    args = ap.parse_args()

    cfg = load_yaml(ROOT / args.config)
    cfg.update({
        "openmc_batches": args.batches,
        "openmc_particles": args.particles_per_batch,
        "openmc_inactive": 0,
        "seed": int(cfg.get("seed", 42)),
        "max_lost_particles": 100000,
    })
    mat_cfg = load_yaml(ROOT / args.materials)
    meta = load_yaml(ROOT / args.particles_meta)
    particles_csv = ROOT / args.particles
    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    specs = specs_from_args(args)
    write_environment_reports(output_root, specs, args.openmc_exec)

    rows: list[dict] = []
    for spec in specs:
        print(f"== running {spec.case_id} ==")
        row = run_openmc_case(spec, cfg, mat_cfg, particles_csv, meta, output_root, args.openmc_exec, args.threads)
        rows.append(row)
        pd.DataFrame(rows).to_csv(output_root / "case_summary_partial.csv", index=False)

    summary = pd.DataFrame(rows)
    summary.to_csv(output_root / "case_summary.csv", index=False)
    summary.to_csv(output_root / "runs_manifest.csv", index=False)
    shifts = build_pairwise_shifts(summary)
    shifts.to_csv(output_root / "pairwise_shifts.csv", index=False)
    print(f"Wrote {output_root}")
    if not shifts.empty:
        print(shifts.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
