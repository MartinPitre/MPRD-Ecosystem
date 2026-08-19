# SUANR_V2

**SUANR_V2 — Uncertainty-Aware Neural Regression**

An experimental machine-learning system designed to combine neural-network regression with explicit uncertainty estimation, calibration, and empirical validation.

> **The incredible becomes credible through evidence.**

---

## Overview

SUANR_V2 explores a simple question:

**Can a regression system provide useful predictions while also communicating meaningful uncertainty about those predictions?**

Instead of treating a prediction as a single unquestioned value, SUANR_V2 is designed to produce both:

- a point prediction, and
- an uncertainty-aware prediction interval.

The project focuses on evaluating whether those uncertainty estimates remain useful across different datasets, confidence levels, training-data sizes, and distribution conditions.

SUANR_V2 is an experimental research project. Results in this repository should be interpreted as empirical observations from the documented tests rather than as claims of universal superiority.

---

## Core Design

SUANR_V2 uses an ensemble-based neural regression architecture.

At a high level:

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

The ensemble provides both a central prediction and information about disagreement between individual models.

Calibration is then used to construct uncertainty intervals intended to correspond to a specified confidence level.

---

## Research Objectives

SUANR_V2 is designed to investigate:

1. **Predictive performance** — How accurately does the model predict unseen observations?
2. **Uncertainty calibration** — Do prediction intervals achieve coverage reasonably close to their intended confidence level?
3. **Robustness** — How does uncertainty behave when the data distribution changes or becomes noisier?
4. **Reduced-data behavior** — What happens when substantially less training data is available?
5. **Cross-dataset behavior** — Are observed properties limited to one dataset, or do they appear across substantially different regression problems?
6. **Repeatability** — Are observed results stable across repeated runs and controlled random seeds?

---

## Validation Program

SUANR_V2 has been evaluated through multiple validation and benchmark experiments rather than relying on a single performance result.

Testing has included:

- interval calibration
- repeated-split stability
- cross-dataset evaluation
- comparison across confidence levels
- distribution-shift testing
- reduced-training-data testing
- benchmark comparison with XGBoost
- repeated-seed evaluation

Datasets used during the research include:

- **Diabetes**
- **California Housing**
- **Friedman #1 synthetic regression**

Each dataset presents a different regression environment and helps test different aspects of the system.

---

## Metrics

### Predictive Performance

**MAE — Mean Absolute Error**

Measures the average absolute difference between predictions and observed values.

**RMSE — Root Mean Squared Error**

Measures prediction error while giving greater weight to larger errors.

**R² — Coefficient of Determination**

Measures how much variation in the target variable is explained by the model.

### Uncertainty Performance

**PICP — Prediction Interval Coverage Probability**

Measures the proportion of observed targets that fall inside the prediction interval.

For a nominal 90% interval, for example, a well-calibrated system should ideally produce empirical coverage reasonably close to 90%.

**MPIW — Mean Prediction Interval Width**

Measures the average width of the prediction intervals.

Coverage alone is not sufficient: extremely wide intervals could achieve high coverage while providing little useful precision. PICP and MPIW therefore need to be interpreted together.

---

## Example Observations

Across the SUANR_V2 experimental program, several useful behaviors have been observed.

Testing has demonstrated that:

- calibrated intervals can approach their intended coverage targets;
- uncertainty behavior can be evaluated across multiple datasets;
- prediction intervals respond to changing data conditions;
- reduced training data can be studied systematically;
- predictive accuracy and uncertainty quality can be evaluated separately;
- repeated-seed testing provides a way to distinguish individual results from more persistent behavior.

These observations apply to the experiments documented in this repository. They should not be interpreted as proof that the same behavior will occur for every dataset or application.

---

## Benchmarking

SUANR_V2 has also been evaluated alongside established machine-learning approaches, including **XGBoost**.

The purpose of these comparisons is not to claim that one model is universally superior.

Instead, benchmarking examines trade-offs between:

- predictive accuracy
- uncertainty information
- calibration
- interval width
- computational cost
- robustness

Different models may perform better under different criteria.

This distinction is important because SUANR_V2 is primarily an investigation into **uncertainty-aware regression**, not simply a competition for the lowest prediction error.

---

## Reproducibility

Where applicable, experiments use controlled:

- random seeds
- train/calibration/test partitions
- model configurations
- confidence levels
- evaluation metrics
- repeated executions

Experimental outputs may include:

```text
CSV
JSON
PNG figures
SHA-256 digests
configuration records
validation summaries
```

These artifacts are intended to make the experimental process inspectable rather than requiring readers to rely only on summarized conclusions.

---

## Repository Structure

Depending on the experiment, this folder may contain:

```text
SUANR_V2/
│
├── Validation_Tests/
│   ├── Test_01/
│   ├── Test_02/
│   ├── Test_03/
│   ├── Test_04/
│   └── Test_05/
│
├── Benchmark_Tests/
│   ├── Benchmark_01/
│   ├── Benchmark_02/
│   ├── Benchmark_03/
│   ├── Benchmark_04/
│   └── Benchmark_05/
│
├── Figures/
├── Results/
├── Documentation/
└── README.md
```

The exact repository structure may evolve as additional experiments are completed.

---

## Experimental Status

**Status:** Active Research / Experimental

SUANR_V2 should not currently be treated as a production-ready machine-learning system.

The project is intended for:

- experimentation
- validation
- benchmarking
- uncertainty research
- reproducibility studies
- integration research with other experimental systems

Further testing may reveal strengths, limitations, failure modes, or necessary architectural changes.

Negative results are considered useful evidence and are retained when they improve understanding of the system.

---

## Related Research

SUANR_V2 is also being investigated as a component within a broader experimental research program involving relational evidence processing and uncertainty-aware decision support.

One integration path is:

```text
SUANR_V2
    ↓
Uncertainty-Aware Evidence
    ↓
MPRD_R
    ↓
Relational Evidence Processing
    ↓
Auditable System State
```

These integrations are separate experimental investigations and should not be interpreted as part of SUANR_V2's standalone predictive performance.

---

## Research Philosophy

The project follows several basic principles:

**Evidence before conclusion.**

A promising result is not automatically a validated result.

**Uncertainty should be visible.**

A system should communicate what it does not know whenever that information can be meaningfully estimated.

**Reproducibility matters.**

Results become more useful when the process that produced them can be inspected and repeated.

**Failure is evidence.**

Unexpected, negative, or contradictory results are retained when they reveal something important about the system.

**Claims should remain proportional to evidence.**

Experimental observations describe what occurred under documented conditions. Broader conclusions require broader evidence.

---

## Author

**Martin Pitre**  
Veteran • Researcher • Explorer

Independent exploration of artificial intelligence, uncertainty-aware systems, relational reasoning, and empirical validation.

---

## Disclaimer

SUANR_V2 is an experimental research project.

The algorithms, results, figures, benchmarks, and documentation contained in this repository are provided for research, educational, and exploratory purposes.

Results obtained from the included experiments do not guarantee equivalent performance on other datasets, environments, or real-world applications.

---

## Guiding Principle

> **The incredible becomes credible through evidence.**
