# SUANR_V2 Validation Test 04

## Cross-Dataset Calibration

SUANR_V2 Validation Test 04 evaluates whether the uncertainty-calibration procedure remains effective across multiple regression datasets with different structures and scales.

The test applies the SUANR_V2 ensemble uncertainty method and calibration procedure independently to three datasets. The principal evaluation measure is prediction-interval coverage probability (PICP) for a nominal 90% prediction interval.

## Objective

Determine whether SUANR_V2 can produce calibrated prediction intervals close to the 90% target across more than one regression problem.

This test addresses cross-dataset calibration behavior. It does not, by itself, establish universal generalization or production readiness.

## Research Question

Does SUANR_V2 maintain useful 90% prediction-interval coverage when evaluated on datasets with different statistical characteristics?

## Datasets

| Dataset | Type | Purpose in the test |
|---|---|---|
| Diabetes | Real-world regression dataset | Evaluates calibration on a small biomedical dataset |
| California Housing | Real-world regression dataset | Evaluates calibration on a larger housing dataset |
| Friedman | Synthetic nonlinear regression dataset | Evaluates calibration on controlled nonlinear data |

## Method Summary

For each dataset, the validation procedure:

1. Loads and prepares the regression data.
2. Divides the observations into model-training, calibration, and test subsets.
3. Trains the SUANR_V2 neural-network ensemble.
4. Uses variation across ensemble predictions to estimate uncertainty.
5. Constructs raw prediction intervals.
6. Applies calibration using data kept separate from the final test subset.
7. Evaluates the calibrated intervals on unseen test observations.
8. Compares empirical coverage with the nominal 90% target.

Keeping calibration and test observations separate is important because the final coverage measurement must be based on data that were not used to determine the calibration adjustment.

## Primary Metric

### Prediction-Interval Coverage Probability

PICP is the proportion of test targets contained within their prediction intervals:

```text
PICP = number of test targets inside their intervals / total test targets
```

For a nominal 90% interval, an observed PICP close to `0.90` indicates that the interval procedure is approximately calibrated for that evaluation.

## Confirmed Results

| Dataset | Target coverage | Calibrated PICP | Difference from target |
|---|---:|---:|---:|
| Diabetes | 0.9000 | 0.9101 | +0.0101 |
| California Housing | 0.9000 | 0.8992 | -0.0008 |
| Friedman | 0.9000 | 0.8550 | -0.0450 |

The mean calibrated coverage across the three datasets was approximately `0.8881`, or `88.81%`.

## Interpretation

- **Diabetes:** Coverage was 1.01 percentage points above the target.
- **California Housing:** Coverage was 0.08 percentage points below the target and was the closest result to 90%.
- **Friedman:** Coverage was 4.50 percentage points below the target, showing weaker calibration than the two real-world datasets.

All three observed coverage values were within five percentage points of the nominal 90% target. The results therefore provide evidence that the calibration procedure transferred across the three evaluated regression settings, while the lower Friedman coverage identifies a limitation that deserves further investigation.

## Evidence Boundary

This validation supports the following limited conclusion:

> In this test configuration, SUANR_V2 produced calibrated 90% prediction intervals with empirical coverage ranging from 85.50% to 91.01% across the Diabetes, California Housing, and Friedman datasets.

The test does not establish that:

- SUANR_V2 will achieve the same coverage on every dataset;
- calibration will remain stable under every random split or distribution shift;
- the intervals are optimally narrow;
- the model is suitable for clinical, financial, safety-critical, or other production decisions; or
- cross-dataset performance has been independently reproduced.

## Reproducibility

To reproduce the validation:

1. Open the Test 04 Python algorithm in Google Colab or another compatible Python environment.
2. Run the complete script without changing the declared configuration.
3. Retain the generated CSV, JSON, figures, console output, and environment details when available.
4. Confirm that each dataset uses separate training, calibration, and test observations.
5. Compare the reproduced PICP values with the results documented above.

Exact software versions, seeds, dataset sizes, model settings, and secondary metrics should be taken from the Test 04 algorithm and its generated evidence files. They are intentionally not inferred in this README when they are not present in the confirmed result record.

## Recommended Repository Contents

```text
SUANR_V2_Validation_Test_04/
├── README.md
├── SUANR_V2_Validation_Test_04.py
├── results/
│   ├── CSV evidence files
│   ├── JSON summary files
│   └── validation figures
└── LICENSE
```

File names may be adjusted to match the actual evidence package.

## Limitations and Next Steps

Recommended follow-up work includes:

- repeated-seed evaluation for each dataset;
- confidence intervals around mean coverage;
- reporting mean and median interval width;
- comparing coverage against interval sharpness;
- testing additional real-world and synthetic datasets;
- evaluating performance under distribution shift;
- comparing SUANR_V2 with conformal and baseline uncertainty methods; and
- independent reproduction by other researchers.

## Project

**SUANR_V2**  
Creator and researcher: **Martin Pitre**

SUANR_V2 is part of the continuing development of the **Multi-Knowledge & Cognitive System (MKCS)** research direction.

> The incredible becomes credible through evidence.

## Citation

When referencing this validation, cite the repository, the Test 04 source code, the associated evidence files, and the version or commit used for the evaluation.

## License

Use of this material is governed by the license included in the repository. Review that license before reusing, modifying, or distributing the code or documentation.
