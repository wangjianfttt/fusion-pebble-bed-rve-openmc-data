# ANE Submission Checklist

## Manuscript

- [x] Target journal set to *Annals of Nuclear Energy*.
- [x] Article type framed as Technical Paper.
- [x] Title updated to "OpenMC hard-sphere RVE study of homogenisation bias in Li4SiO4/Be pebble beds".
- [x] Abstract is a single paragraph and <=250 words.
- [x] Claims are local, source-normalised RVE responses, not full-blanket TBR margins.
- [x] TPR6, total H3-production and full-blanket TBR terminology are separated.
- [x] Boundary-condition sensitivity included from newly generated OpenMC results.
- [x] Photon-transport heating sensitivity included from newly generated OpenMC results.
- [x] ENDF/B-VIII.0 and FENDL-3.2c neutron-data sensitivities included from newly generated OpenMC libraries.
- [x] Data availability includes the GitHub repository and Zenodo DOI.

## Data And Reproducibility

- [x] Baseline PF=0.618 data are traceable to `data/openmc_results/hardsphere_pf_sweep_production/`.
- [x] New all-reflective boundary statepoints are stored under `results/sensitivity/pf618_boundary_reflective_10x5k/`.
- [x] New photon-transport statepoints are stored under `results/sensitivity/pf618_photon_80x30k/`.
- [x] New ENDF/B-VIII.0 statepoints are stored under `results/sensitivity/pf618_endfb80_80x30k/`.
- [x] Combined case manifest written to `results/runs_manifest.csv`.
- [x] Combined case summary written to `results/case_summary.csv`.
- [x] Combined pairwise shifts written to `results/pairwise_shifts.csv`.
- [x] Software and cross-section reports written to `results/software_versions.txt` and `results/cross_section_libraries.txt`.
- [x] ENDF/B-VIII.0 OpenMC data generated from official NNDC source files and PF=0.618 baseline pair rerun.
- [x] FENDL-3.2c neutron ACE data downloaded locally from IAEA, converted to OpenMC HDF5 on `/data1`, and PF=0.618 baseline pair rerun.

## Build

- [x] Main elsarticle source builds with `latexmk -pdf -interaction=nonstopmode -halt-on-error ane_elsarticle_hardsphere.tex`.
- [x] Flat elsarticle source builds with the same command in `manuscript/submission_ane_flat/`.
- [x] No unresolved references or fatal LaTeX errors in the checked build.
- [x] No table overfull warnings remain; only a small page-output overfull warning is present.

## Author Actions Before Upload

- [ ] Confirm author order, affiliations and corresponding-author metadata.
- [ ] Confirm funding and acknowledgements.
- [x] Repository DOI inserted: `10.5281/zenodo.20636518`.
- [x] Modern-library sensitivity decision resolved for ENDF/B-VIII.0 and FENDL-3.2c targeted neutron-data checks.
