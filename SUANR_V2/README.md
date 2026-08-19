# SUANR_V2

**SUANR_V2 — Uncertainty-Aware Neural Regression**

An experimental machine-learning system designed to combine neural-network
regression with explicit uncertainty estimation, calibration, and empirical
validation.

> **The incredible becomes credible through evidence.**

---

## Creator and License

**Creator:** Martin Pitre  
**Copyright © 2026 Martin Pitre. All rights reserved except as expressly granted
by the included license.**

SUANR_V2 is released under the custom **SUANR_V2 Research and Evaluation
License v1.0**.

The repository may be studied, tested, evaluated, and used for permitted
non-commercial research and educational purposes under that license.

**Commercial use is not granted. Prior written permission from Martin Pitre is
required before commercial use.**

See:

- [`LICENSE`](LICENSE)
- [`NOTICE.md`](NOTICE.md)
- [`COMMERCIAL_USE.md`](COMMERCIAL_USE.md)
- [`CITATION.cff`](CITATION.cff)
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

---

## Overview

SUANR_V2 explores a central question:

**Can a regression system provide useful predictions while also communicating
meaningful uncertainty about those predictions?**

Instead of treating a prediction as a single unquestioned value, SUANR_V2 is
designed to produce both:

- a point prediction; and
- an uncertainty-aware prediction interval.

The project evaluates uncertainty behavior across different datasets,
confidence levels, training-data sizes, random seeds, and distribution
conditions.

SUANR_V2 is experimental research software. Results should be interpreted as
empirical observations from documented tests rather than claims of universal
superiority.

---

## Core Design

```text
Input Data
    ↓
Preprocessing / Partitioning
    ↓
Neural Regression Ensemble
    ↓
Individual Model Predictions
    ↓
Ensemble Prediction
    ↓
Epistemic Uncertainty Estimate
    ↓
Calibration
    ↓
Prediction Interval
    ↓
Prediction + Explicit Uncertainty
```

The ensemble provides a central prediction together with information derived
from disagreement between individual models. Calibration is used to construct
uncertainty intervals intended to correspond to a specified confidence level.

---

## Research Objectives

SUANR_V2 investigates:

1. **Predictive performance** — accuracy on unseen observations.
2. **Uncertainty calibration** — whether interval coverage approaches the
   intended confidence level.
3. **Robustness** — how predictions and uncertainty respond to changing or
   noisier data conditions.
4. **Reduced-data behavior** — performance when less training data is available.
5. **Cross-dataset behavior** — whether observations persist across different
   regression problems.
6. **Repeatability** — stability across controlled random seeds and repeated
   executions.

---

## Validation Program

Testing has included:

- interval calibration;
- repeated-split stability;
- cross-dataset evaluation;
- comparison across confidence levels;
- distribution-shift testing;
- reduced-training-data testing;
- benchmark comparison with XGBoost; and
- repeated-seed evaluation.

Datasets used in the experimental program include:

- **Diabetes**
- **California Housing**
- **Friedman #1 synthetic regression**

---

## Metrics

### Predictive Performance

**MAE — Mean Absolute Error**  
Average absolute difference between predictions and observed values.

**RMSE — Root Mean Squared Error**  
Prediction error metric that gives greater weight to larger errors.

**R² — Coefficient of Determination**  
Measures how much variation in the target is explained by the model.

### Uncertainty Performance

**PICP — Prediction Interval Coverage Probability**  
The proportion of observed target values falling inside the prediction
interval.

**MPIW — Mean Prediction Interval Width**  
The average width of prediction intervals.

PICP and MPIW should be interpreted together: high coverage achieved only
through extremely wide intervals may provide limited practical precision.

---

## Benchmarking

SUANR_V2 has been evaluated alongside established machine-learning approaches,
including XGBoost.

These comparisons examine trade-offs involving:

- predictive accuracy;
- uncertainty information;
- calibration;
- interval width;
- computational cost; and
- robustness.

The purpose is not to assert that a single model is universally superior.

---

## Reproducibility

Where applicable, experiments use controlled:

- random seeds;
- train/calibration/test partitions;
- model configurations;
- confidence levels;
- evaluation metrics; and
- repeated executions.

Experimental outputs may include CSV, JSON, PNG figures, configuration records,
validation summaries, and SHA-256 audit digests.

---

## Citation

If you use, evaluate, adapt, benchmark, or materially discuss SUANR_V2 in
research or technical work, please cite the project.

GitHub can read the repository's [`CITATION.cff`](CITATION.cff) file and expose
citation information directly from the repository interface.

Suggested human-readable form:

> Pitre, Martin. (2026). *SUANR_V2: Uncertainty-Aware Neural Regression*,
> version 2.0. Software.

If a DOI or archived release identifier is created later, the citation metadata
should be updated accordingly.

---

## Experimental Status

**Status: Active Research / Experimental**

SUANR_V2 should not currently be treated as production-ready software or as a
validated system for high-stakes deployment.

Further testing may identify strengths, limitations, failure modes, or
architectural changes.

Negative and contradictory results are considered evidence and should be
preserved when they improve understanding of the system.

---

## Research Philosophy

**Evidence before conclusion.**  
A promising result is not automatically a validated result.

**Uncertainty should be visible.**  
A system should communicate what it does not know whenever that information can
be meaningfully estimated.

**Reproducibility matters.**  
Results become more useful when the process that produced them can be inspected
and repeated.

**Failure is evidence.**  
Unexpected or negative results can reveal important properties of a system.

**Claims should remain proportional to evidence.**  
Experimental observations describe documented conditions. Broader conclusions
require broader evidence.

---

## Author

**Martin Pitre**  
Veteran • Researcher • Explorer

Independent exploration of artificial intelligence, uncertainty-aware systems,
relational reasoning, and empirical validation.

---

## Disclaimer

SUANR_V2 is experimental research software. The software, algorithms, figures,
benchmarks, and documentation are provided for research, educational, and
exploratory purposes under the terms of the included license.

Results obtained in documented experiments do not guarantee equivalent
performance on other datasets, environments, or real-world applications.

See [`LICENSE`](LICENSE) for the complete legal terms.
