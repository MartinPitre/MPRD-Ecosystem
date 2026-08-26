# SUANR_V2 — Phase 1 Validation Tests

This folder contains the four Phase 1 validation tests for **SUANR_V2**, an experimental uncertainty-aware neural-network regression framework developed by **Martin Pitre**.

Phase 1 evaluated whether the framework could:

1. Generate experimental predictive intervals.
2. Calibrate those intervals toward a nominal 90% coverage target.
3. Maintain calibration across repeated data splits.
4. Generalize across multiple regression datasets.

## Phase 1 outcome

The four tests form a progressive validation sequence. Test 01 established the baseline limitation of uncalibrated stochastic intervals. Test 02 introduced split-conformal calibration. Test 03 evaluated repeated-split stability. Test 04 tested cross-dataset generalization and completed Phase 1.

| Test | Validation objective | Key result | Status |
|---|---|---|---|
| Test 01 | 90% predictive-interval feasibility | Raw coverage: 4.49%; interval width: 11.89 | Feasibility result — no calibration claim |
| Test 02 | Residual calibration and interval reliability | Coverage improved from 10.11% to 87.64% | PASS |
| Test 03 | Repeated-split calibration stability | Mean calibrated coverage: 90.30% across 30/30 successful runs | PASS |
| Test 04 | Cross-dataset generalization | Final coverage remained within the declared 85%–95% acceptance range on all three datasets | PASS — Phase 1 completion supported |

## Validation Test 01 — Predictive Interval Feasibility

### Objective

Determine whether the frozen SUANR_V1 stochastic prediction mechanism could be extended to produce an experimental 90% predictive interval using the 5th and 95th percentiles of repeated predictions.

### Method

- Dataset: scikit-learn Diabetes dataset
- Train/test split: 80%/20%
- Test observations: 89
- Hidden layers: `(64, 32)`
- Stochastic prediction samples: 50
- Input-noise level: 0.05
- Experimental bounds: 5th and 95th percentiles

### Results

| Metric | Result |
|---|---:|
| MAE | 41.5830 |
| RMSE | 51.9781 |
| Target coverage | 90.00% |
| Empirical coverage | 4.49% |
| Coverage gap | −85.51 percentage points |
| Mean interval width | 11.8886 |
| Pearson uncertainty/error correlation | 0.3396 |
| Spearman uncertainty/error correlation | 0.2853 |

### Interpretation

The stochastic predictions produced measurable dispersion, and uncertainty showed a modest positive relationship with absolute error. However, the percentile interval was far too narrow and did not provide calibrated 90% coverage.

This was a scientifically useful feasibility result: it identified the need for an explicit calibration stage and directly motivated Validation Test 02.

## Validation Test 02 — Interval Calibration

### Objective

Evaluate whether split-conformal residual calibration could improve empirical interval coverage toward the intended 90% level without changing point-prediction accuracy.

### Method

- Dataset: scikit-learn Diabetes dataset
- Split: 265 training, 88 calibration, and 89 test observations
- Nominal interval coverage: 90%
- Calibration approach: split-conformal residual calibration

### Results

| Metric | Raw | Calibrated |
|---|---:|---:|
| Empirical coverage | 10.11% | 87.64% |
| Mean interval width | 20.8425 | 205.7491 |

| Additional metric | Result |
|---|---:|
| Coverage gap after calibration | −2.36 percentage points |
| MAE | 49.9556 |
| RMSE | 62.8929 |
| Error–uncertainty correlation | 0.0279 |
| Error–entropy correlation | 0.1689 |

### Interpretation

Split-conformal calibration substantially improved coverage while leaving point-prediction accuracy unchanged. The improvement was achieved by widening the intervals considerably, establishing interval reliability under the fixed test configuration while also identifying interval sharpness as an area for future research.

**Result: PASS**

## Validation Test 03 — Repeated-Split Calibration Stability

### Objective

Determine whether the calibrated results remain stable across repeated random training, calibration, and test splits rather than depending on a single favorable partition.

### Method

- Dataset: scikit-learn Diabetes dataset
- Runs: 30
- Successful runs: 30
- Split per run: 60% training, 20% calibration, and 20% testing
- Ensemble members: 8
- Nominal interval coverage: 90%

### Results

| Metric | Mean | Range or supporting result |
|---|---:|---:|
| MAE | 45.2663 | 38.6250–51.8953 |
| RMSE | 56.4370 | 49.8377–65.9495 |
| Raw coverage | 27.34% | 19.10%–39.33% |
| Calibrated coverage | 90.30% | 80.90%–98.88% |
| Raw mean interval width | 41.1432 | 31.6717–55.9474 |
| Calibrated mean interval width | 188.0043 | 161.6586–227.1196 |

Calibration improved coverage in every run. All intervals were valid, all 30 runs completed successfully, and every predefined acceptance criterion passed.

**Result: PASS**

## Validation Test 04 — Cross-Dataset Generalization

### Objective

Evaluate whether SUANR_V2 maintains predictive accuracy and calibrated 90% conformal intervals across regression datasets with different statistical characteristics.

### Datasets

- Diabetes — built-in control dataset
- California Housing — real-world housing regression dataset
- Friedman #1 — synthetic nonlinear regression dataset

### Final results

| Dataset | MAE | RMSE | Calibrated coverage | Calibration error | Result |
|---|---:|---:|---:|---:|---|
| Diabetes | 45.9736 | 56.4954 | 91.01% | +1.01 percentage points | PASS |
| California Housing | 0.3606 | 0.5219 | 89.92% | −0.08 percentage points | PASS |
| Friedman #1 | 0.9597 | 1.2072 | 85.50% | −4.50 percentage points | PASS |

All datasets satisfied the declared 85%–95% coverage range and ±5 percentage-point calibration-error threshold. The completed run provided evidence that the calibration framework was not limited to the original Diabetes dataset.

**Result: PASS — Phase 1 completion supported**

## Overall interpretation

Phase 1 produced evidence for four progressively stronger conclusions:

- Stochastic prediction dispersion alone did not create reliable 90% intervals.
- Split-conformal calibration substantially corrected interval undercoverage.
- Calibrated coverage remained stable across 30 repeated data splits.
- The calibrated framework generalized across real-world and synthetic regression datasets in the final cross-dataset test.

These results support continued evaluation of SUANR_V2. They do not establish universal performance, production readiness, or superiority over established machine-learning methods.

## Reproducibility

Run each validation script in a Python environment containing the dependencies used by that test. The principal packages are:

```text
numpy
pandas
scipy
scikit-learn
matplotlib
```

Test 01 also imports the frozen SUANR_V1 implementation:

```python
from suanr_v1 import SUANR_v1
```

Place `suanr_v1.py` where Python can import it before running Test 01.

Example:

```bash
python SUANR_V2_Test_01_90_Percent_Predictive_Interval.py
```

Where supported, the scripts generate machine-readable CSV and JSON evidence files, figures, execution summaries, and packaged validation artifacts.

## Scientific boundaries

- Predictive-interval coverage is empirical and specific to the declared datasets, partitions, seeds, and configurations.
- Conformal prediction provides a marginal coverage guarantee under its statistical assumptions; it does not guarantee correct coverage for every individual observation or subgroup.
- Wider intervals can improve coverage while reducing sharpness and practical usefulness.
- Test 01 is retained as evidence of the uncalibrated baseline limitation, not as evidence of successful 90% calibration.
- Phase 1 validates the experimental framework under controlled conditions. Independent replication and broader external validation remain necessary.

## Project status

Phase 1 is complete. Subsequent SUANR_V2 work moves from foundational validation toward comparative benchmarking, distribution-shift testing, confidence-level analysis, reduced-data evaluation, and integration research.

## Author

**Martin Pitre**  
SUANR_V2 Project

> The incredible becomes credible through evidence.

## Citation

If you use or discuss this validation package, please cite the project, version, test number, repository URL, and access date. See the repository's `CITATION.cff` file when available.

## License

See the `LICENSE` and `NOTICE` files in the repository for permitted use and attribution requirements.
