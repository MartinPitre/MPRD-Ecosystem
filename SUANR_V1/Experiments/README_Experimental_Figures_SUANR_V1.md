# Experimental Figures

This folder contains experimental and benchmark figures related to the development, evaluation, and preservation of SUANR v1.

These figures are retained to document model behavior, testing results, comparative performance, and historical development decisions.

---

## Diabetes Benchmark: MAE and RMSE (100 Runs)

**File:**  
`SUANR_v1_Diabetes_Benchmark_MAE_RMSE_100_Runs.png`

### Purpose

This figure compares the predictive performance of:

- Linear Regression
- Random Forest Regressor
- SUANR v1

using the Diabetes dataset over 100 benchmark runs.

### Metrics

- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)

### Interpretation

The benchmark evaluates predictive accuracy only.

Results indicate that:

- Linear Regression achieved the lowest error on this dataset.
- Random Forest and SUANR v1 produced similar error levels.
- SUANR v1 was not designed solely to minimize prediction error.

### Research Context

The primary objective of SUANR v1 is uncertainty-aware prediction.

In addition to generating predictions, SUANR v1 produces uncertainty estimates intended to help identify:

- Higher-risk predictions
- Lower-confidence regions
- Areas where additional caution may be warranted.

Therefore, this benchmark should be interpreted as a predictive-error comparison rather than a complete assessment of SUANR v1 capabilities.

### Historical Significance

This figure is preserved as part of the original SUANR v1 research record and provides a baseline reference for future uncertainty-aware model development.

---

## Preservation Note

Experimental figures are retained even when results are neutral or unfavorable.

Preservation supports:

- Transparency
- Reproducibility
- Historical traceability
- Future comparison studies

---

**SUANR v1**  
*Stochastic Uncertainty-Aware Neural Regression*

**Author:** Martin Pitre

"The incredible becomes credible through evidence."

— Martin Pitre
