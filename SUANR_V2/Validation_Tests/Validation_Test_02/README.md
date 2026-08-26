# SUANR_V2 Validation Test 02 — Interval Calibration

## Overview

This validation test evaluates whether split conformal calibration can improve the empirical coverage of SUANR_V2 prediction intervals while preserving point-prediction accuracy.

The test was performed on the scikit-learn diabetes regression dataset using a fixed train/calibration/test split and a target prediction-interval coverage of 90%.

**Overall result: PASS**

Calibration increased empirical coverage from **10.11%** to **87.64%**. The calibrated result was **2.36 percentage points below** the 90% target and remained within the declared maximum acceptable coverage gap of 5 percentage points. MAE and RMSE were unchanged because calibration expanded the intervals without altering the point predictions.

## Test Objective

The test asks whether interval calibration can:

1. Move empirical coverage closer to the 90% target.
2. Reduce the coverage gap by a meaningful amount.
3. Keep interval width within the declared practical limit.
4. Preserve point-prediction accuracy.

## Dataset and Split

| Item | Value |
|---|---:|
| Dataset | scikit-learn diabetes dataset |
| Total observations | 442 |
| Training observations | 265 |
| Calibration observations | 88 |
| Test observations | 89 |
| Target coverage | 90% |
| Alpha | 0.10 |
| Random state | 42 |

## Method

SUANR_V2 produced raw stochastic prediction intervals from 200 stochastic samples using the 5th and 95th percentiles. The test then applied **split conformal additive interval expansion** to the separate calibration set.

The conformal correction was:

- `q_hat = 92.453290`
- Conformal rank: `81`
- Adjusted quantile probability: `0.920455`

The calibrated lower and upper bounds were obtained by subtracting and adding `q_hat` to the raw interval bounds. This changed interval coverage and width but did not change the predicted means.

## Model Configuration

| Parameter | Value |
|---|---:|
| Hidden layers | `(64, 32)` |
| Stochastic noise | 0.05 |
| Stochastic samples | 200 |
| Lower percentile | 5th |
| Upper percentile | 95th |
| Entropy bins | 10 |
| Maximum iterations | 3,000 |

## Results

### Raw and Calibrated Intervals

| Metric | Raw intervals | Calibrated intervals | Change |
|---|---:|---:|---:|
| Empirical coverage | 0.1011 (10.11%) | 0.8764 (87.64%) | +0.7753 |
| Coverage gap from 90% | 0.7989 | 0.0236 | −0.7753 |
| Mean interval width | 20.8425 | 205.7491 | +184.9066 |
| Median interval width | 20.5123 | 205.4189 | +184.9066 |
| MAE | 49.9556 | 49.9556 | 0.0000 |
| RMSE | 62.8929 | 62.8929 | 0.0000 |

Additional observations:

- Mean interval-width multiplier: **9.8716×**
- Calibrated mean-width-to-MAE ratio: **4.1186**
- Correlation between uncertainty and absolute error: **0.0279** (`p = 0.7956`)
- Correlation between entropy and absolute error: **0.1689** (`p = 0.1135`)

The correlation results were weak and not statistically significant in this test. The PASS decision is based on interval calibration performance and preservation of regression accuracy, not on evidence of a strong uncertainty–error or entropy–error relationship.

## Acceptance Criteria

| Criterion | Threshold | Observed result | Decision |
|---|---:|---:|---|
| Coverage moved closer to target | Required | Yes | PASS |
| Maximum final coverage gap | ≤ 0.05 | 0.0236 | PASS |
| Minimum coverage-gap improvement | ≥ 0.02 | 0.7753 | PASS |
| Maximum calibrated width-to-MAE ratio | ≤ 5.00 | 4.1186 | PASS |
| Maximum allowed MAE change | ≤ 1 × 10⁻¹⁰ | 0.0000 | PASS |
| Maximum allowed RMSE change | ≤ 1 × 10⁻¹⁰ | 0.0000 | PASS |

## Validation Decision

**PASS**

Calibration moved empirical coverage substantially closer to the 90% target. The final coverage gap met the declared tolerance, the calibrated interval width remained within the declared practical threshold, and point-prediction accuracy was preserved.

This result demonstrates successful calibration for this specific experimental configuration. It does not establish universal calibration performance.

## Repository Files

| File | Description |
|---|---|
| `SUANR_V2_Test_02_Evidence.csv` | Per-observation predictions, errors, uncertainty values, raw intervals, calibrated intervals, widths, and coverage indicators |
| `SUANR_V2_Test_02_Calibration_Evidence.csv` | Calibration-set evidence used to calculate the conformal correction |
| `SUANR_V2_Test_02_Summary.json` | Structured configuration, metrics, thresholds, environment, and PASS decision |
| `SUANR_V2_Test_02_Validation_Report.txt` | Plain-text validation summary |
| `SUANR_V2_Test_02_Coverage.png` | Raw and calibrated empirical coverage comparison |
| `SUANR_V2_Test_02_Interval_Widths.png` | Raw and calibrated interval-width comparison |
| `SUANR_V2_Test_02_Prediction_Intervals.png` | Prediction intervals and observed targets for the test set |

## Reproducibility Environment

| Software | Version |
|---|---:|
| Python | 3.13.15 |
| NumPy | 2.1.3 |
| pandas | 2.2.3 |
| SciPy | 1.16.3 |
| scikit-learn | 1.6.1 |

Minor numerical differences may occur when the test is repeated with different software versions, platforms, or numerical backends.

## Scientific Boundary

The result applies to this fixed dataset, split, seed, model configuration, and calibration strategy. Broader reliability claims require repeated-seed validation, alternative data splits, and external-dataset testing.

## Author

**Martin Pitre**  
SUANR_V2 Project

## Project Principle

*The incredible becomes credible through evidence.*
