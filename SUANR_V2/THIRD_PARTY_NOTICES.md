# Third-Party Notices

SUANR_V2 may rely on third-party software libraries, datasets, tools, or
services. Those materials are not relicensed under the SUANR_V2 Research and
Evaluation License.

Users are responsible for complying with the terms applicable to each
third-party dependency and dataset.

## Common software dependencies

Depending on the specific experiment or notebook, SUANR_V2 may use software
from the Python scientific and machine-learning ecosystem, including packages
such as:

- Python
- NumPy
- pandas
- SciPy
- scikit-learn
- Matplotlib
- XGBoost, where benchmark comparisons use it

Each dependency remains subject to its own license. Package versions and the
actual dependency set should be confirmed from the code or environment used for
a particular experiment.

## Datasets

SUANR_V2 experiments have included datasets such as:

### Diabetes regression dataset

Experiments may use the diabetes regression dataset distributed through
scikit-learn. Users should consult the scikit-learn dataset documentation and
the underlying dataset/source information before redistribution or external use.

### California Housing dataset

Experiments may use the California Housing dataset made available through
scikit-learn. Users should consult the scikit-learn documentation and original
dataset/source terms before redistribution or external use.

### Friedman #1 synthetic regression data

Some experiments use synthetically generated Friedman #1 regression data,
commonly generated through scikit-learn's dataset utilities. The generated
experimental data and the software used to generate it should be distinguished
from third-party implementations and documentation.

## Benchmark systems

Where SUANR_V2 is compared with XGBoost or another third-party model,
the third-party implementation remains governed by its own license and is not
part of the SUANR_V2 licensing grant.

## Repository maintenance

Before each public release, this file should be checked against:

- imported packages;
- copied or adapted code;
- included datasets;
- included model files;
- icons, images, fonts, or other media;
- external documentation incorporated into the repository.

If a third-party component requires a copyright notice, attribution, license
text, or citation, add it here or include the required notice file alongside
the relevant material.
