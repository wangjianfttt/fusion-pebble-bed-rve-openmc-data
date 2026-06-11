# Annals of Nuclear Energy Submission Manifest

This directory contains the current hard-sphere manuscript package.  It is
separate from the legacy `manuscript/submission/` FED-oriented package.

## Primary Upload Candidates

- `manuscript_ane_elsarticle_hardsphere.pdf`  
  Preferred ANE/Elsevier preprint PDF compiled from `ane_elsarticle_hardsphere.tex`.
- `ane_elsarticle_hardsphere.tex`  
  Preferred Elsevier `elsarticle` LaTeX source for Annals of Nuclear Energy.
- `manuscript_ane_hardsphere.pdf`  
  Article-class traceability PDF compiled from `paper_final_en.tex`.
- `paper_final_en.tex`  
  Article-class source retained for traceability.
- `highlights.txt`  
  Five manuscript highlights aligned with the hard-sphere evidence chain.
- `cover_letter_draft.md`  
  Draft cover letter for Annals of Nuclear Energy.
- `ANE_submission_checklist.md`  
  Internal final upload checklist.

## Main Figures

- `figures/fig1_microstructure.pdf`
- `figures/mechanism_pf62_be_fraction_shifts.pdf`
- `figures/hardsphere_pf_sweep_shifts.pdf`
- `figures/hardsphere_pf618_seed_replicates.pdf`
- `figures/hardsphere_pf618_spectrum.pdf`
- `figures/hardsphere_pf618_midplane_mesh_shifts.pdf`
- `figures/li2o_fns_mixed_p0741_openmc_vs_sato_digitized.pdf`

## Supporting Data

- `supporting_data/hardsphere_pf618_baseline_tallies.tex`
- `supporting_data/hardsphere_pf_sweep_shifts_with_uncertainty.csv`
- `supporting_data/mechanism_pf62_shifts_with_uncertainty.csv`
- `supporting_data/hardsphere_pf618_seed_replicates_summary.csv`
- `supporting_data/hardsphere_pf618_spectrum_integral_metrics.csv`
- `supporting_data/hardsphere_pf618_midplane_mesh_shifts.csv`
- `supporting_data/li2o_fns_mixed_p0741_openmc_vs_sato_digitized.csv`
- `tables/pf618_sensitivity_summary.tex`
- `../../results/runs_manifest.csv`
- `../../results/case_summary.csv`
- `../../results/pairwise_shifts.csv`
- `../../results/software_versions.txt`
- `../../results/cross_section_libraries.txt`
- `../../results/sensitivity/pf618_endfb80_80x30k/`
- `../../data_package/README.md`

## Internal Preparation Files

These files are useful for author review and reviewer-response preparation, but
should not be uploaded unless requested:

- `readiness_audit.md`
- `claim_evidence_matrix.md`
- `reviewer_risk_register.md`

## Do Not Upload From The Legacy Package

The following legacy files are inconsistent with the current hard-sphere
manuscript unless regenerated:

- `manuscript/submission/fed_elsarticle_submission.*`
- `manuscript/submission/output/fed_elsarticle_submission.pdf`
- `manuscript/submission/output/supplementary_information.pdf`
- `submission_bundle_lightweight.zip`
- `submission_bundle_full_figures.zip`
- legacy figures `fig3_pf_feedback.*`, `fig4_spatial_maps.*`, and old
  `fig5_mechanism_sweep.*`.

## Remaining Author Actions

- Confirm author order, affiliations and corresponding-author information.
- Confirm funding, acknowledgements and CRediT contribution statement.
- Insert public repository DOI or accession link in the Data and code availability statement.
- FENDL-3.2c PF=0.618 baseline rerun is complete under `results/sensitivity/pf618_fendl32c_80x30k/`; no FENDL rerun remains as an author action.
- Confirm whether Annals of Nuclear Energy requires separate source files,
  highlights and/or graphical abstract at initial submission.
- Run one final PDF visual inspection before upload.
