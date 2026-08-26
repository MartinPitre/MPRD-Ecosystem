# SUANR_V2 Core Algorithm

**Stochastic Uncertainty-Aware Neural Regression**

SUANR_V2 is an experimental neural-regression algorithm that produces a point estimate together with several measures derived from a distribution of stochastic predictions.

The core implementation standardizes the input features, trains a scikit-learn `MLPRegressor`, repeatedly perturbs the standardized inputs with Gaussian noise, and summarizes the resulting predictions.

**Author:** Martin Pitre  
**Version:** Core Algorithm v1.0  
**Status:** Experimental research software

> This folder contains the core algorithm only. It does not contain an embedded dataset, validation test, benchmark, reporting system, trained model, or file-output routine.

## Purpose

Most regression models return a single predicted value. SUANR_V2 also examines how its predictions vary when small stochastic perturbations are applied to the standardized input features.

For every observation, the algorithm returns:

- the mean stochastic prediction;
- the standard deviation of the stochastic predictions;
- histogram-based prediction-distribution entropy;
- empirical lower and upper percentile bounds; and
- the width between those bounds.

These outputs are intended to support uncertainty-aware experimentation, comparison, and further calibration research.

## How it works

1. Validate the input features and target values.
2. Standardize the features with `StandardScaler`.
3. Train an `MLPRegressor` on the standardized features.
4. During prediction, add Gaussian noise to the standardized inputs.
5. Repeat prediction for the configured number of stochastic samples.
6. Summarize the sampled prediction distribution for each observation.

## Scientific boundary

The lower and upper bounds produced by this core describe the empirical percentiles of predictions generated through stochastic input perturbation.

They **must not be described as calibrated prediction intervals** unless a separate calibration procedure has measured and verified their empirical coverage on appropriate held-out data.

Likewise, the reported standard deviation and entropy are properties of this sampling procedure. They do not, by themselves, quantify every source of real-world predictive uncertainty.

## Requirements

- Python 3.10 or newer
- NumPy
- SciPy
- scikit-learn

Install the dependencies with:

```bash
python -m pip install numpy scipy scikit-learn
```

## Folder contents

```text
SUANR_V2/
├── README.md
└── SUANR_V2_Core_Algorithm_v1_0.py
```

## Quick start

```python
import numpy as np

from SUANR_V2_Core_Algorithm_v1_0 import SUANR_V2


# Replace these example arrays with your own regression dataset.
X_train = np.array(
    [
        [1.0, 2.0],
        [2.0, 1.0],
        [3.0, 4.0],
        [4.0, 3.0],
        [5.0, 6.0],
        [6.0, 5.0],
    ]
)
y_train = np.array([3.1, 3.0, 7.2, 7.0, 11.1, 10.9])
X_new = np.array([[2.5, 3.0], [5.5, 4.5]])

model = SUANR_V2(
    hidden_layer_sizes=(64, 32),
    stochastic_noise=0.05,
    n_samples=50,
    lower_percentile=5.0,
    upper_percentile=95.0,
    random_state=42,
)

model.fit(X_train, y_train)
result = model.predict(X_new)

print("Mean:", result.mean)
print("Uncertainty standard deviation:", result.uncertainty_std)
print("Entropy:", result.entropy)
print("Lower bound:", result.lower_bound)
print("Upper bound:", result.upper_bound)
print("Interval width:", result.interval_width)
```

To obtain only the stochastic mean prediction:

```python
mean_prediction = model.predict_mean(X_new)
```

To inspect the complete stochastic sample matrix:

```python
samples = model.collect_stochastic_predictions(X_new)
print(samples.shape)  # (n_samples, n_observations)
```

## Main parameters

| Parameter | Default | Description |
| --- | ---: | --- |
| `hidden_layer_sizes` | `(64, 32)` | Hidden-layer architecture passed to `MLPRegressor`. |
| `stochastic_noise` | `0.05` | Standard deviation of Gaussian noise added to standardized inputs. |
| `n_samples` | `50` | Number of stochastic prediction samples. |
| `lower_percentile` | `5.0` | Percentile used for the empirical lower bound. |
| `upper_percentile` | `95.0` | Percentile used for the empirical upper bound. |
| `entropy_bins` | `10` | Histogram-bin count used to estimate prediction-distribution entropy. |
| `random_state` | `42` | Seed used for neural-network fitting and stochastic sampling. |
| `max_iter` | `2000` | Maximum number of `MLPRegressor` training iterations. |

The default percentile span is 90%, but this is a **nominal percentile span**, not a verified 90% coverage claim.

## Prediction result

`predict()` returns an immutable `SUANRPrediction` object containing NumPy arrays:

| Field | Meaning |
| --- | --- |
| `mean` | Mean across the stochastic predictions. |
| `uncertainty_std` | Standard deviation across the stochastic predictions. |
| `entropy` | Entropy of the histogram of sampled predictions. |
| `lower_bound` | Selected empirical lower percentile. |
| `upper_bound` | Selected empirical upper percentile. |
| `interval_width` | Difference between the upper and lower bounds. |

## Reproducibility

When `random_state` is fixed, the model fitting process and the stochastic sampling sequence are seeded. Repeated calls using the same fitted model and the same inputs are therefore designed to return the same sampled results.

Changing the seed, training data, hyperparameters, dependency versions, or execution environment may change the results.

## Input expectations

- `X` must contain finite numeric values and may be a one- or two-dimensional array-like object.
- A one-dimensional `X` is interpreted as one observation with multiple features.
- `y` must be a finite one-dimensional target array.
- Prediction inputs must have the same number of features used during fitting.

The core does not automatically impute missing values, encode categorical variables, select features, tune hyperparameters, split datasets, or calibrate intervals.

## Current limitations

- This is experimental research code and is not presented as production-ready software.
- Uncertainty is estimated through input perturbation around a single trained neural network.
- The empirical percentile bounds are not automatically calibrated for coverage.
- Entropy depends on the selected histogram-bin count and sampled prediction distribution.
- Input noise is applied in standardized feature space and should be assessed for the dataset and application.
- Model quality and uncertainty behavior depend on the data, preprocessing, parameters, and evaluation design.
- The core has no built-in persistence, visualization, reporting, or dataset-management system.

## Validation and responsible interpretation

Any claimed performance should be tied to a named dataset, documented data split, evaluation metric, random seed or repeated-seed procedure, and reproducible test code.

Recommended evaluation measures include:

- MAE, RMSE, and R² for point-prediction performance;
- empirical coverage and mean interval width when a separate interval-calibration method is used;
- repeated-seed and repeated-split stability;
- behavior under distribution shift, reduced training data, and noise; and
- comparison with clearly identified baseline models.

Results from one dataset or experiment should not be generalized to unrelated settings without further evidence.

## Intended use

SUANR_V2 is intended for:

- regression research and education;
- uncertainty-aware model experimentation;
- reproducible validation studies;
- comparison with baseline regression approaches; and
- development of separately tested calibration or decision-support layers.

It should not be used as the sole basis for medical, legal, financial, safety-critical, or other high-impact decisions.

## Project direction

SUANR_V2 is being explored as an uncertainty-assessment component within the broader **MKCS — Multi-Knowledge & Cognitive System** research direction. This repository establishes the standalone core and does not claim that a complete MKCS implementation or real-world control system is present in this folder.

## Citation

If you use or discuss this implementation, please identify it as:

> Pitre, Martin. *SUANR_V2 Core Algorithm v1.0: Stochastic Uncertainty-Aware Neural Regression.* 2026.

Repository-specific citation metadata may be added separately in a `CITATION.cff` file.

## License

No license terms are stated in this README. Add a `LICENSE` file before public release to clearly define permitted use, modification, and distribution.

Unless a license is added, the presence of source code in a public repository should not be interpreted as granting reuse rights.

## Disclaimer

This software is provided for research and educational purposes. It comes without guarantees of accuracy, fitness for a particular purpose, or suitability for deployment. Users are responsible for independently validating the algorithm and its outputs for their own data and application.

---

**The incredible becomes credible through evidence.**
