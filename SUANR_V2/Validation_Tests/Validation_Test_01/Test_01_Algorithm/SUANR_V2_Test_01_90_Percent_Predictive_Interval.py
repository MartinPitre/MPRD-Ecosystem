"""
SUANR_V2 Test 01 — 90% Predictive Interval Feasibility

Purpose
-------
Preserve the frozen SUANR_V1 implementation as the control model and add
an experimental empirical 90% predictive interval using the 5th and 95th
percentiles of SUANR_V1 stochastic forward predictions.

This is a feasibility test only. The resulting interval is not claimed to be
calibrated until empirical coverage and interval width have been evaluated.

Author: Martin Pitre
Project: SUANR_V2
Reference baseline: SUANR_V1 (frozen and published)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.datasets import load_diabetes
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

from suanr_v1 import SUANR_v1


@dataclass(frozen=True)
class TestConfiguration:
    test_size: float = 0.20
    split_random_state: int = 42
    model_random_state: int = 42
    hidden_layer_sizes: tuple[int, int] = (64, 32)
    stochastic_noise: float = 0.05
    n_samples: int = 50
    lower_percentile: float = 5.0
    upper_percentile: float = 95.0


@dataclass(frozen=True)
class TestMetrics:
    n_test_observations: int
    mae: float
    rmse: float
    empirical_coverage: float
    target_coverage: float
    coverage_gap: float
    mean_interval_width: float
    median_interval_width: float
    min_interval_width: float
    max_interval_width: float
    pearson_uncertainty_error: float
    pearson_uncertainty_error_pvalue: float
    spearman_uncertainty_error: float
    spearman_uncertainty_error_pvalue: float
    pearson_entropy_error: float
    pearson_entropy_error_pvalue: float
    spearman_entropy_error: float
    spearman_entropy_error_pvalue: float


def _safe_correlation(function: Any, x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Return a finite correlation and p-value, or NaN when undefined."""
    if len(x) < 2 or np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return float("nan"), float("nan")
    result = function(x, y)
    return float(result.statistic), float(result.pvalue)


def collect_stochastic_predictions(model: SUANR_v1, X: np.ndarray) -> np.ndarray:
    """
    Reproduce the frozen SUANR_V1 stochastic sampling mechanism without
    modifying the baseline class.

    Returns
    -------
    np.ndarray
        Shape: (n_samples, n_observations)
    """
    X_scaled = model.scaler.transform(X)
    rng = np.random.default_rng(model.random_state)
    samples: list[np.ndarray] = []

    for _ in range(model.n_samples):
        noisy_X = X_scaled + rng.normal(0, model.stochastic_noise, X_scaled.shape)
        samples.append(model.model.predict(noisy_X))

    return np.asarray(samples, dtype=float)


def histogram_entropy_by_observation(predictions: np.ndarray, bins: int = 10) -> np.ndarray:
    """Match the SUANR_V1 histogram-entropy calculation for each observation."""
    from scipy.stats import entropy

    values: list[float] = []
    for index in range(predictions.shape[1]):
        histogram, _ = np.histogram(predictions[:, index], bins=bins, density=True)
        histogram = histogram + 1e-10
        values.append(float(entropy(histogram)))
    return np.asarray(values)


def run_test(config: TestConfiguration) -> tuple[TestMetrics, pd.DataFrame]:
    """Run SUANR_V2 Test 01 and return summary metrics plus row-level evidence."""
    dataset = load_diabetes()
    X = np.asarray(dataset.data, dtype=float)
    y = np.asarray(dataset.target, dtype=float)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=config.test_size,
        random_state=config.split_random_state,
    )

    # Frozen SUANR_V1 control model. No baseline source code is altered.
    control = SUANR_v1(
        hidden_layer_sizes=config.hidden_layer_sizes,
        stochastic_noise=config.stochastic_noise,
        n_samples=config.n_samples,
        random_state=config.model_random_state,
    )
    control.fit(X_train, y_train)

    stochastic_predictions = collect_stochastic_predictions(control, X_test)

    mean_prediction = np.mean(stochastic_predictions, axis=0)
    uncertainty = np.std(stochastic_predictions, axis=0)
    entropy_values = histogram_entropy_by_observation(stochastic_predictions)

    lower_bound = np.percentile(
        stochastic_predictions, config.lower_percentile, axis=0
    )
    upper_bound = np.percentile(
        stochastic_predictions, config.upper_percentile, axis=0
    )

    interval_width = upper_bound - lower_bound
    covered = (y_test >= lower_bound) & (y_test <= upper_bound)
    absolute_error = np.abs(y_test - mean_prediction)

    mae = float(mean_absolute_error(y_test, mean_prediction))
    rmse = float(np.sqrt(mean_squared_error(y_test, mean_prediction)))
    empirical_coverage = float(np.mean(covered))
    target_coverage = (config.upper_percentile - config.lower_percentile) / 100.0

    pearson_u, pearson_u_p = _safe_correlation(
        pearsonr, uncertainty, absolute_error
    )
    spearman_u, spearman_u_p = _safe_correlation(
        spearmanr, uncertainty, absolute_error
    )
    pearson_e, pearson_e_p = _safe_correlation(
        pearsonr, entropy_values, absolute_error
    )
    spearman_e, spearman_e_p = _safe_correlation(
        spearmanr, entropy_values, absolute_error
    )

    metrics = TestMetrics(
        n_test_observations=int(len(y_test)),
        mae=mae,
        rmse=rmse,
        empirical_coverage=empirical_coverage,
        target_coverage=target_coverage,
        coverage_gap=empirical_coverage - target_coverage,
        mean_interval_width=float(np.mean(interval_width)),
        median_interval_width=float(np.median(interval_width)),
        min_interval_width=float(np.min(interval_width)),
        max_interval_width=float(np.max(interval_width)),
        pearson_uncertainty_error=pearson_u,
        pearson_uncertainty_error_pvalue=pearson_u_p,
        spearman_uncertainty_error=spearman_u,
        spearman_uncertainty_error_pvalue=spearman_u_p,
        pearson_entropy_error=pearson_e,
        pearson_entropy_error_pvalue=pearson_e_p,
        spearman_entropy_error=spearman_e,
        spearman_entropy_error_pvalue=spearman_e_p,
    )

    evidence = pd.DataFrame(
        {
            "observation_id": np.arange(len(y_test), dtype=int),
            "true_target": y_test,
            "mean_prediction": mean_prediction,
            "absolute_error": absolute_error,
            "uncertainty_std": uncertainty,
            "entropy": entropy_values,
            "lower_5th_percentile": lower_bound,
            "upper_95th_percentile": upper_bound,
            "interval_width": interval_width,
            "covered_by_90_percent_interval": covered,
        }
    )

    return metrics, evidence


def save_results(
    output_directory: Path,
    config: TestConfiguration,
    metrics: TestMetrics,
    evidence: pd.DataFrame,
) -> None:
    """Save machine-readable summary and row-level evidence files."""
    output_directory.mkdir(parents=True, exist_ok=True)

    evidence.to_csv(output_directory / "SUANR_V2_Test_01_Evidence.csv", index=False)

    payload = {
        "test_name": "SUANR_V2 Predictive Interval Prototype Test 01",
        "status": "Feasibility experiment — no calibration claim",
        "configuration": asdict(config),
        "metrics": asdict(metrics),
        "interpretation_boundary": (
            "The 5th–95th percentile interval reflects dispersion from input-noise "
            "stochastic sampling. It is not a validated 90% prediction interval "
            "unless empirical calibration is demonstrated."
        ),
    }
    with (output_directory / "SUANR_V2_Test_01_Summary.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(payload, file, indent=2)


def print_summary(metrics: TestMetrics) -> None:
    """Print a concise scientific summary to the console."""
    print("\nSUANR_V2 TEST 01 — 90% PREDICTIVE INTERVAL FEASIBILITY")
    print("=" * 64)
    print(f"Test observations:               {metrics.n_test_observations}")
    print(f"MAE:                             {metrics.mae:.4f}")
    print(f"RMSE:                            {metrics.rmse:.4f}")
    print(f"Target interval coverage:        {metrics.target_coverage:.2%}")
    print(f"Empirical interval coverage:     {metrics.empirical_coverage:.2%}")
    print(f"Coverage gap:                    {metrics.coverage_gap:+.2%}")
    print(f"Mean interval width:             {metrics.mean_interval_width:.4f}")
    print(f"Median interval width:           {metrics.median_interval_width:.4f}")
    print(
        "Pearson uncertainty/error:      "
        f"{metrics.pearson_uncertainty_error:.4f} "
        f"(p={metrics.pearson_uncertainty_error_pvalue:.4g})"
    )
    print(
        "Spearman uncertainty/error:     "
        f"{metrics.spearman_uncertainty_error:.4f} "
        f"(p={metrics.spearman_uncertainty_error_pvalue:.4g})"
    )
    print(
        "Pearson entropy/error:          "
        f"{metrics.pearson_entropy_error:.4f} "
        f"(p={metrics.pearson_entropy_error_pvalue:.4g})"
    )
    print(
        "Spearman entropy/error:         "
        f"{metrics.spearman_entropy_error:.4f} "
        f"(p={metrics.spearman_entropy_error_pvalue:.4g})"
    )
    print("\nInterpretation boundary:")
    print(
        "This test evaluates feasibility only. Percentile bounds from stochastic "
        "input perturbations are not automatically calibrated prediction intervals."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run SUANR_V2 Test 01 using the frozen SUANR_V1 control."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("SUANR_V2_Test_01_Results"),
        help="Directory for CSV and JSON results.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = TestConfiguration()
    metrics, evidence = run_test(config)
    save_results(args.output_dir, config, metrics, evidence)
    print_summary(metrics)
    print(f"\nResults saved to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
