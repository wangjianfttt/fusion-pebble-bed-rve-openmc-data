# Cover Letter

Dear Editor,

We submit the manuscript entitled "Pebble-scale topology effects on homogenised neutronics of Li4SiO4/Be breeder beds" for consideration as a full-length research article in *Fusion Engineering and Design*.

The manuscript addresses a modelling issue directly relevant to fusion breeder-blanket engineering: how pebble-scale He void topology and discrete breeder--multiplier interfaces affect local neutronic responses when a Li4SiO4/Be breeder bed is represented by a volume-homogenised material. This question is important for fusion blanket design workflows because homogenised material descriptions are routinely used in sector and full-device Monte Carlo models, whereas local pebble-scale topology can alter fast-neutron streaming, Be multiplier exposure, tritium-production response, and heating-score redistribution.

The work uses paired OpenMC calculations with matched material inventories, strict non-overlapping hard-sphere geometry audits, propagated tally uncertainties, packing-fraction and Be-fraction sensitivity studies, independent packing realisations, boundary-condition sensitivity, photon-transport heating sensitivity, and ENDF/B-VIII.0/FENDL-3.2c neutron-data sensitivity reruns. These elements are intended to provide a reproducible fusion-blanket modelling assessment rather than a generic code-comparison exercise. The study is deliberately framed as a source-normalised local representative-volume-element analysis, not as a full-blanket tritium breeding ratio margin or a final blanket design calculation.

The main engineering implication is that connected void topology in Li4SiO4/Be breeder beds can change the partitioning of local multiplication, tritium-production response, flux, and OpenMC heating-score response even when the homogenised and geometry-resolved models use the same total material inventory. The manuscript therefore provides practical evidence for when homogenised blanket neutronics models should be interpreted cautiously and where geometry-resolved checks may be warranted.

The processed particle lists, OpenMC input-generation scripts, post-processing scripts, result CSV files, figure source data, and manuscript build files are publicly available through the project data repository and Zenodo DOI 10.5281/zenodo.20636518. Continuous-energy nuclear-data libraries are not redistributed because of size and licensing constraints; the exact library names, source URLs, processing tools, checksums, and local `cross_sections.xml` paths used in the calculations are recorded in the data package.

We confirm that this manuscript is original, is not under consideration elsewhere, and that all authors have approved its submission to *Fusion Engineering and Design*.

Sincerely,

Jian Wang
