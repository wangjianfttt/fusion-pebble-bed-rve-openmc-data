# FED Submission Checklist

## Manuscript

- [x] Target journal set to *Fusion Engineering and Design*.
- [x] Article framed as a full-length research article for fusion blanket modelling.
- [x] Title retained as "Pebble-scale topology effects on homogenised neutronics of Li4SiO4/Be breeder beds".
- [x] Claims are local, source-normalised RVE responses, not full-blanket TBR margins.
- [x] TPR6, total H3-production and full-blanket TBR terminology are separated.
- [x] Boundary-condition sensitivity included from generated OpenMC results.
- [x] Photon-transport heating sensitivity included from generated OpenMC results.
- [x] ENDF/B-VIII.0 and FENDL-3.2c neutron-data sensitivities included.
- [x] Data availability includes the GitHub repository and Zenodo DOI.

## FED Reframing

- [x] Cover letter emphasises fusion breeder-blanket modelling implications.
- [x] Highlights emphasise homogenisation use in fusion breeder-blanket workflows.
- [x] Package avoids presenting the work as a generic OpenMC code-comparison study.
- [x] Engineering scope remains leakage-sensitive and RVE-local.

## Build

- [x] Build `fed_elsarticle_topology.tex` with `latexmk -pdf -interaction=nonstopmode -halt-on-error fed_elsarticle_topology.tex`.
- [x] Confirm no unresolved references or fatal LaTeX errors.
- [x] Visually inspect the generated PDF before upload.
- [x] Confirm Word cover letter renders cleanly.

## Author Actions Before Upload

- [ ] Confirm author order, affiliations and corresponding-author metadata.
- [ ] Confirm funding and acknowledgements.
- [ ] Confirm repository DOI remains accessible: `10.5281/zenodo.20636518`.
