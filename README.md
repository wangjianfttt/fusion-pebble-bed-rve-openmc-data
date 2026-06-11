# Data Package README

This data package describes the reproducibility materials for the Annals of Nuclear Energy manuscript "OpenMC hard-sphere RVE study of homogenisation bias in Li4SiO4/Be pebble beds".

## Scope

The calculations are local, source-normalised representative volume element (RVE) OpenMC calculations.  They do not represent full-blanket tritium breeding ratio margins.

## Key Inputs

- `config/base_config.yaml`: RVE dimensions, source definition and OpenMC run settings.
- `config/materials.yaml`: Li4SiO4, Be and He material definitions.
- `data/openmc_results/hardsphere_pf_sweep_production/particle_variants/particles_pf6180.csv`: audited PF=0.618 hard-sphere particle list.
- `data/openmc_results/hardsphere_pf_sweep_production/particle_variants/particles_pf6180_meta.yaml`: geometry audit metadata for the PF=0.618 particle list.

## Reproduction Scripts

- `scripts/run_pf618_sensitivity.py`: generates and runs paired PF=0.618 sensitivity cases.
- `scripts/collect_sensitivity_results.py`: combines baseline, boundary and photon results into manuscript CSV files.
- `scripts/build_sensitivity_table.py`: builds the LaTeX sensitivity table from `results/pairwise_shifts.csv`.
- `scripts/audit_tallies.py`: audits OpenMC tally values, units and propagated uncertainties.
- `scripts/audit_geometry_inventory.py`: audits packing fraction, overlaps and material inventory.

## Result Directories

- `data/openmc_results/hardsphere_pf_sweep_production/`: baseline axial-vacuum PF sweep.
- `results/sensitivity/pf618_boundary_reflective_10x5k/`: all-reflective PF=0.618 sensitivity pair.
- `results/sensitivity/pf618_photon_80x30k/`: photon-transport PF=0.618 heating-sensitivity pair.
- `results/sensitivity/pf618_endfb80_80x30k/`: ENDF/B-VIII.0 PF=0.618 neutron-data sensitivity pair.
- `results/sensitivity/pf618_fendl32c_80x30k/`: FENDL-3.2c PF=0.618 neutron-data sensitivity pair.
- `results/case_summary.csv`: combined case-level tally summary.
- `results/pairwise_shifts.csv`: combined resolved--homogenised relative shifts with propagated 1 sigma uncertainty.
- `results/runs_manifest.csv`: run manifest with settings, paths and statepoints.
- `results/software_versions.txt`: OpenMC and Python environment report.
- `results/cross_section_libraries.txt`: cross-section library paths and modern-library search status.

## Nuclear Data

The main production runs used ENDF/B-VII.1 NNDC HDF5 data via `/home/wangjian/openmc_data/endfb-vii.1-hdf5/cross_sections.xml` on the remote workstation.  Targeted PF=0.618 neutron-data sensitivity pairs were also run with a minimal ENDF/B-VIII.0 library generated from official NNDC source files and with a FENDL-3.2c neutron ACE library downloaded locally from the IAEA, transferred to `/data1`, and converted to OpenMC HDF5.  Continuous-energy nuclear-data HDF5 libraries and large statepoint files are not redistributed in this lightweight package.

## Build Commands

From the repository root:

```bash
python scripts/collect_sensitivity_results.py
python scripts/build_sensitivity_table.py
cd manuscript/submission_ane
latexmk -pdf -interaction=nonstopmode -halt-on-error ane_elsarticle_hardsphere.tex
```

The flat submission source can be built in `manuscript/submission_ane_flat/` with the same `latexmk` command.
