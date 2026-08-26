# SUANR_V2 — Validation Test 01

## Predictive Interval Prototype and Feasibility Experiment

SUANR_V2 Validation Test 01 evaluates an early uncertainty-estimation prototype for regression. The experiment uses repeated stochastic predictions to examine whether prediction dispersion contains useful information about model error.

This test is a **feasibility experiment**, not evidence of a calibrated prediction interval.

## Test objective

The test was designed to determine whether:

1. stochastic input perturbations can produce a measurable distribution of predictions;
2. the standard deviation of those predictions is associated with absolute prediction error;
3. percentile bounds derived from the stochastic samples provide adequate empirical coverage; and
4. entropy offers useful additional information about prediction error.

## Experimental configuration

| Parameter | Value |
|---|---:|
| Test split | 20% |
| Data-split random state | 42 |
| Model random state | 42 |
| Hidden layers | 64, 32 |
| Stochastic input-noise level | 0.05 |
| Stochastic samples per observation | 50 |
| Lower percentile | 5th |
| Upper percentile | 95th |
| Nominal interval coverage | 90% |
| Test observations | 89 |

For each test observation, the prototype generated 50 predictions after applying stochastic input noise. The mean prediction was used as the point estimate. The 5th and 95th percentiles formed the prototype interval, while the standard deviation and entropy of the sampled predictions were recorded as uncertainty measures.

## Results

| Metric | Result |
|---|---:|
| Mean absolute error (MAE) | 41.5830 |
| Root mean squared error (RMSE) | 51.9781 |
| Empirical interval coverage | 4.49% |
| Target interval coverage | 90.00% |
| Coverage gap | −85.51 percentage points |
| Mean interval width | 11.8886 |
| Median interval width | 12.0324 |
| Minimum interval width | 6.3092 |
| Maximum interval width | 17.2122 |

Only 4 of the 89 test targets fell within the prototype 5th–95th percentile bounds. The resulting 4.49% empirical coverage was far below the nominal 90% target, showing that the intervals were severely underestimated and were not calibrated prediction intervals.

## Uncertainty–error relationships

| Comparison | Correlation | p-value |
|---|---:|---:|
| Pearson: uncertainty standard deviation vs. absolute error | 0.3396 | 0.00113 |
| Spearman: uncertainty standard deviation vs. absolute error | 0.2853 | 0.00673 |
| Pearson: entropy vs. absolute error | −0.1521 | 0.15484 |
| Spearman: entropy vs. absolute error | −0.0962 | 0.36989 |

The stochastic prediction standard deviation had a modest positive relationship with absolute error under both Pearson and Spearman analysis. In this experiment, observations with greater sampled prediction dispersion tended to have larger prediction errors.

The entropy measurements did not show a statistically significant relationship with absolute error at the conventional 0.05 significance level.

## Interpretation

Test 01 produced two different findings:

- **Useful feasibility signal:** stochastic prediction dispersion showed a modest positive association with prediction error.
- **Failed interval calibration:** the percentile interval covered only 4.49% of test targets instead of the intended 90%.

The 5th–95th percentile bounds reflect only the dispersion created by the selected input-noise sampling procedure. They do not capture all sources of predictive uncertainty and must not be described as validated 90% prediction intervals.

The low coverage result provided direct evidence that a formal calibration method was required. This finding motivated subsequent SUANR_V2 work on empirically calibrated uncertainty intervals.

## Evidence files

- `SUANR_V2_Test_01_Evidence.csv` — observation-level targets, predictions, errors, uncertainty measures, percentile bounds, interval widths, and coverage results.
- `SUANR_V2_Test_01_Summary.json` — test configuration, aggregate metrics, correlation results, and the formal interpretation boundary.

## Reproducibility notes

The data split and model initialization both used random state `42`. The retained evidence files provide the complete observation-level outputs and aggregate results needed to audit the reported metrics.

Exact reproduction also requires the original Test 01 implementation, dependency versions, preprocessing procedure, and source dataset.

## Scope and limitations

- This was an early prototype test on a single train/test split.
- The experiment does not establish generalization across datasets, random seeds, or distribution shifts.
- Statistical significance does not by itself establish that an uncertainty measure is sufficiently strong or calibrated for operational use.
- The reported percentile bounds are stochastic-dispersion intervals, not validated predictive-confidence guarantees.
- No safety-critical, clinical, financial, or autonomous decision should rely on this prototype result.

## Test status

**FEASIBILITY EXPERIMENT — NO CALIBRATION CLAIM**

The test successfully identified a potentially useful uncertainty signal and, equally importantly, documented that the original percentile-interval method was not calibrated.

## Project

**SUANR_V2**  
Creator: Martin Pitre  
Motto: *The incredible becomes credible through evidence.*

