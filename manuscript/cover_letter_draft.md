# Cover Letter Draft

Dear Editor,

We submit the manuscript entitled "OpenMC hard-sphere RVE study of homogenisation bias in Li4SiO4/Be pebble beds" for consideration as a Technical Paper in *Annals of Nuclear Energy*.

The manuscript addresses a modelling question relevant to fusion breeder-blanket neutronics: how much local source-normalised response can be changed when a Li4SiO4/Be pebble bed is represented by a volume-homogenised material instead of an explicit pebble-scale RVE.  The work uses paired OpenMC calculations with matched material inventories, strict hard-sphere geometry audits, propagated tally uncertainties, boundary-condition sensitivity and photon-transport heating sensitivity.  The study is deliberately framed as a local homogenisation-bias analysis, not as a full-blanket TBR margin or blanket design calculation.

The revised manuscript now includes an executable Li2O/FNS screening benchmark, audited PF=0.618 baseline results, a PF sweep, Be-fraction sensitivity, independent packing realisations, an all-reflective boundary check, a photon-transport heating check and ENDF/B-VIII.0/FENDL-3.2c neutron-data sensitivity reruns.  Both nuclear-data reruns preserve the sign and approximate magnitude of the local homogenisation-bias trend.  The manuscript treats these as targeted neutron-data checks, not as a full nuclear-data uncertainty analysis.

All processed input files, scripts, result CSV files, statepoint-derived tables and figure source data will be deposited in a public repository before submission finalisation.  Continuous-energy nuclear-data libraries will not be redistributed; exact library names and `cross_sections.xml` paths are recorded in the data package.

Sincerely,

Jian Wang
