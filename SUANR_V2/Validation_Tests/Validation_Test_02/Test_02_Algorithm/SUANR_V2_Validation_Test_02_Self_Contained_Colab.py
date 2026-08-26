"""
SUANR_V2 Validation Test 02 — Self-Contained Google Colab Edition
Interval Calibration by Split Conformal Expansion

Author: Martin Pitre
Created: 27 July 2026
Project: SUANR_V2
Status: Executable validation test
Dependencies: numpy, scipy, pandas, matplotlib, scikit-learn

HOW TO USE IN GOOGLE COLAB
--------------------------
1. Open a new Google Colab notebook.
2. Copy this entire file into one code cell.
3. Press Run.
4. Review the printed summary and generated evidence files.

TEST PURPOSE
------------
Test whether calibration can move SUANR_V2's empirical interval coverage
closer to the intended 90% target without changing point predictions or
materially harming predictive accuracy.

CALIBRATION METHOD
------------------
The model is fitted only on the training partition. Raw empirical percentile
intervals are produced on a separate calibration partition. A split-conformal
nonconformity score measures how far each true calibration target lies outside
its raw interval:

    score = max(lower - y, y - upper, 0)

The finite-sample conformal quantile of these scores is then added to both
sides of every raw test interval:

    calibrated lower = raw lower - q_hat
    calibrated upper = raw upper + q_hat

The test partition is never used to choose q_hat.

SCIENTIFIC BOUNDARY
-------------------
This test evaluates one calibration strategy on one fixed train/calibration/
test split of the scikit-learn diabetes dataset. A PASS supports this specific
validation configuration; it is not universal proof of calibration across all
datasets, populations, random seeds, or deployment conditions.
"""

from __future__ import annotations

import json
import math
import platform
import sys
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
from numpy.typing import ArrayLike, NDArray
from scipy.stats import entropy, pearsonr
from sklearn.datasets import load_diabetes
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted


# =============================================================================
# CONFIGURATION
# =============================================================================

TEST_NAME = "SUANR_V2 Validation Test 02 — Interval Calibration"
OUTPUT_DIRECTORY = Path("SUANR_V2_Test_02_Results")

RANDOM_STATE = 42
TARGET_COVERAGE = 0.90
ALPHA = 1.0 - TARGET_COVERAGE

# First split: 60% train, 40% temporary.
# Second split: temporary is divided equally into 20% calibration and 20% test.
TEST_SIZE_FROM_FULL = 0.20
CALIBRATION_SIZE_FROM_FULL = 0.20

HIDDEN_LAYER_SIZES = (64, 32)
STOCHASTIC_NOISE = 0.05
N_STOCHASTIC_SAMPLES = 200
LOWER_PERCENTILE = 5.0
UPPER_PERCENTILE = 95.0
ENTROPY_BINS = 10
MAX_ITER = 3000

# Explicit validation thresholds.
MAX_ACCEPTABLE_COVERAGE_GAP = 0.05
MINIMUM_GAP_IMPROVEMENT = 0.02
MAX_WIDTH_TO_MAE_RATIO = 5.0
MAX_ALLOWED_MAE_CHANGE = 1e-10
MAX_ALLOWED_RMSE_CHANGE = 1e-10


FloatArray = NDArray[np.float64]


# =============================================================================
# SUANR_V2 CORE ALGORITHM
# =============================================================================

@dataclass(frozen=True)
class SUANRPrediction:
    """Prediction results for one or more observations."""

    mean: FloatArray
    uncertainty_std: FloatArray
    entropy: FloatArray
    lower_bound: FloatArray
    upper_bound: FloatArray
    interval_width: FloatArray


class SUANR_V2:
    """
    Neural regression model with stochastic uncertainty estimates and
    empirical percentile bounds.
    """

    def __init__(
        self,
        hidden_layer_sizes: tuple[int, ...] = (64, 32),
        stochastic_noise: float = 0.05,
        n_samples: int = 50,
        lower_percentile: float = 5.0,
        upper_percentile: float = 95.0,
        entropy_bins: int = 10,
        random_state: int | None = 42,
        max_iter: int = 2000,
    ) -> None:
        self.hidden_layer_sizes = hidden_layer_sizes
        self.stochastic_noise = stochastic_noise
        self.n_samples = n_samples
        self.lower_percentile = lower_percentile
        self.upper_percentile = upper_percentile
        self.entropy_bins = entropy_bins
        self.random_state = random_state
        self.max_iter = max_iter

        self._validate_parameters()

        self.scaler = StandardScaler()
        self.model = MLPRegressor(
            hidden_layer_sizes=self.hidden_layer_sizes,
            activation="relu",
            solver="adam",
            random_state=self.random_state,
            max_iter=self.max_iter,
        )

    @property
    def nominal_interval_coverage(self) -> float:
        """Return the percentile span as a proportion, not a calibration claim."""
        return (self.upper_percentile - self.lower_percentile) / 100.0

    def fit(self, X: ArrayLike, y: ArrayLike) -> "SUANR_V2":
        """Fit the input scaler and neural regression model."""
        X_array = self._as_2d_float_array(X, name="X")
        y_array = np.asarray(y, dtype=float)

        if y_array.ndim != 1:
            raise ValueError("y must be a one-dimensional target array.")
        if X_array.shape[0] != y_array.shape[0]:
            raise ValueError("X and y must contain the same number of observations.")
        if not np.all(np.isfinite(y_array)):
            raise ValueError("y contains NaN or infinite values.")

        X_scaled = self.scaler.fit_transform(X_array)
        self.model.fit(X_scaled, y_array)
        self.n_features_in_ = X_array.shape[1]
        return self

    def collect_stochastic_predictions(self, X: ArrayLike) -> FloatArray:
        """Generate stochastic predictions with shape (samples, observations)."""
        self._check_fitted()
        X_array = self._validate_prediction_input(X)
        X_scaled = self.scaler.transform(X_array)
        rng = np.random.default_rng(self.random_state)

        samples = np.empty((self.n_samples, X_scaled.shape[0]), dtype=float)
        for sample_index in range(self.n_samples):
            noise = rng.normal(0.0, self.stochastic_noise, X_scaled.shape)
            samples[sample_index] = self.model.predict(X_scaled + noise)

        return samples

    def predict(self, X: ArrayLike) -> SUANRPrediction:
        """Return mean predictions, uncertainty measures, and percentile bounds."""
        samples = self.collect_stochastic_predictions(X)

        mean = np.mean(samples, axis=0)
        uncertainty_std = np.std(samples, axis=0)
        entropy_values = self._histogram_entropy(samples)
        lower_bound = np.percentile(samples, self.lower_percentile, axis=0)
        upper_bound = np.percentile(samples, self.upper_percentile, axis=0)

        return SUANRPrediction(
            mean=np.asarray(mean, dtype=float),
            uncertainty_std=np.asarray(uncertainty_std, dtype=float),
            entropy=np.asarray(entropy_values, dtype=float),
            lower_bound=np.asarray(lower_bound, dtype=float),
            upper_bound=np.asarray(upper_bound, dtype=float),
            interval_width=np.asarray(upper_bound - lower_bound, dtype=float),
        )

    def predict_mean(self, X: ArrayLike) -> FloatArray:
        """Return only the stochastic mean prediction."""
        return self.predict(X).mean

    def _histogram_entropy(self, predictions: FloatArray) -> FloatArray:
        values = np.empty(predictions.shape[1], dtype=float)

        for observation_index in range(predictions.shape[1]):
            histogram, _ = np.histogram(
                predictions[:, observation_index],
                bins=self.entropy_bins,
                density=True,
            )
            values[observation_index] = float(entropy(histogram + 1e-10))

        return values

    def _validate_parameters(self) -> None:
        if not self.hidden_layer_sizes or any(size <= 0 for size in self.hidden_layer_sizes):
            raise ValueError("hidden_layer_sizes must contain positive integers.")
        if self.stochastic_noise < 0:
            raise ValueError("stochastic_noise must be non-negative.")
        if self.n_samples < 2:
            raise ValueError("n_samples must be at least 2.")
        if not 0.0 <= self.lower_percentile < self.upper_percentile <= 100.0:
            raise ValueError(
                "Percentiles must satisfy 0 <= lower_percentile < "
                "upper_percentile <= 100."
            )
        if self.entropy_bins < 2:
            raise ValueError("entropy_bins must be at least 2.")
        if self.max_iter <= 0:
            raise ValueError("max_iter must be positive.")

    def _check_fitted(self) -> None:
        check_is_fitted(self.scaler)
        check_is_fitted(self.model)
        if not hasattr(self, "n_features_in_"):
            raise RuntimeError("The SUANR_V2 model has not been fitted.")

    def _validate_prediction_input(self, X: ArrayLike) -> FloatArray:
        X_array = self._as_2d_float_array(X, name="X")
        if X_array.shape[1] != self.n_features_in_:
            raise ValueError(
                f"X has {X_array.shape[1]} features, but the fitted model expects "
                f"{self.n_features_in_}."
            )
        return X_array

    @staticmethod
    def _as_2d_float_array(X: ArrayLike, name: str) -> FloatArray:
        array = np.asarray(X, dtype=float)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        if array.ndim != 2:
            raise ValueError(f"{name} must be a one- or two-dimensional array.")
        if array.shape[0] == 0 or array.shape[1] == 0:
            raise ValueError(f"{name} must not be empty.")
        if not np.all(np.isfinite(array)):
            raise ValueError(f"{name} contains NaN or infinite values.")
        return np.asarray(array, dtype=float)


__all__: Iterable[str] = ("SUANR_V2", "SUANRPrediction")


# =============================================================================
# TEST DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class IntervalMetrics:
    empirical_coverage: float
    coverage_gap: float
    mean_interval_width: float
    median_interval_width: float


@dataclass(frozen=True)
class RegressionMetrics:
    mae: float
    rmse: float
    uncertainty_error_correlation: float
    uncertainty_error_p_value: float
    entropy_error_correlation: float
    entropy_error_p_value: float


@dataclass(frozen=True)
class ValidationDecision:
    overall_result: str
    coverage_moved_closer: bool
    coverage_gap_within_tolerance: bool
    substantial_gap_improvement: bool
    interval_width_practical: bool
    regression_accuracy_preserved: bool
    explanation: str


# =============================================================================
# CALIBRATION AND METRIC FUNCTIONS
# =============================================================================

def finite_sample_conformal_quantile(
    scores: ArrayLike,
    target_coverage: float,
) -> tuple[float, int, float]:
    """
    Return the split-conformal finite-sample quantile.

    The adjusted probability is:
        ceil((n + 1) * target_coverage) / n

    It is capped at 1.0 and evaluated using NumPy's "higher" method.
    """
    score_array = np.asarray(scores, dtype=float)

    if score_array.ndim != 1 or score_array.size == 0:
        raise ValueError("scores must be a non-empty one-dimensional array.")
    if not np.all(np.isfinite(score_array)):
        raise ValueError("scores contains NaN or infinite values.")
    if not 0.0 < target_coverage < 1.0:
        raise ValueError("target_coverage must be strictly between 0 and 1.")

    n = score_array.size
    rank = min(math.ceil((n + 1) * target_coverage), n)
    adjusted_probability = rank / n
    q_hat = float(np.quantile(score_array, adjusted_probability, method="higher"))
    return q_hat, rank, adjusted_probability


def interval_nonconformity_scores(
    y_true: ArrayLike,
    lower: ArrayLike,
    upper: ArrayLike,
) -> FloatArray:
    """Measure the distance by which targets fall outside raw intervals."""
    y_array = np.asarray(y_true, dtype=float)
    lower_array = np.asarray(lower, dtype=float)
    upper_array = np.asarray(upper, dtype=float)

    if not (y_array.shape == lower_array.shape == upper_array.shape):
        raise ValueError("y_true, lower, and upper must have matching shapes.")

    scores = np.maximum.reduce(
        [
            lower_array - y_array,
            y_array - upper_array,
            np.zeros_like(y_array),
        ]
    )
    return np.asarray(scores, dtype=float)


def calculate_interval_metrics(
    y_true: ArrayLike,
    lower: ArrayLike,
    upper: ArrayLike,
    target_coverage: float,
) -> IntervalMetrics:
    y_array = np.asarray(y_true, dtype=float)
    lower_array = np.asarray(lower, dtype=float)
    upper_array = np.asarray(upper, dtype=float)

    covered = (y_array >= lower_array) & (y_array <= upper_array)
    widths = upper_array - lower_array
    empirical_coverage = float(np.mean(covered))

    return IntervalMetrics(
        empirical_coverage=empirical_coverage,
        coverage_gap=abs(empirical_coverage - target_coverage),
        mean_interval_width=float(np.mean(widths)),
        median_interval_width=float(np.median(widths)),
    )


def safe_pearson_correlation(
    first: ArrayLike,
    second: ArrayLike,
) -> tuple[float, float]:
    """Return Pearson r and p-value, or NaN when correlation is undefined."""
    first_array = np.asarray(first, dtype=float)
    second_array = np.asarray(second, dtype=float)

    if first_array.size < 2:
        return float("nan"), float("nan")
    if np.isclose(np.std(first_array), 0.0) or np.isclose(np.std(second_array), 0.0):
        return float("nan"), float("nan")

    result = pearsonr(first_array, second_array)
    return float(result.statistic), float(result.pvalue)


def calculate_regression_metrics(
    y_true: ArrayLike,
    prediction: SUANRPrediction,
) -> RegressionMetrics:
    y_array = np.asarray(y_true, dtype=float)
    absolute_error = np.abs(y_array - prediction.mean)

    uncertainty_r, uncertainty_p = safe_pearson_correlation(
        prediction.uncertainty_std,
        absolute_error,
    )
    entropy_r, entropy_p = safe_pearson_correlation(
        prediction.entropy,
        absolute_error,
    )

    return RegressionMetrics(
        mae=float(mean_absolute_error(y_array, prediction.mean)),
        rmse=float(np.sqrt(mean_squared_error(y_array, prediction.mean))),
        uncertainty_error_correlation=uncertainty_r,
        uncertainty_error_p_value=uncertainty_p,
        entropy_error_correlation=entropy_r,
        entropy_error_p_value=entropy_p,
    )


def make_validation_decision(
    raw_intervals: IntervalMetrics,
    calibrated_intervals: IntervalMetrics,
    raw_regression: RegressionMetrics,
    calibrated_regression: RegressionMetrics,
) -> ValidationDecision:
    gap_improvement = raw_intervals.coverage_gap - calibrated_intervals.coverage_gap
    coverage_moved_closer = calibrated_intervals.coverage_gap < raw_intervals.coverage_gap
    gap_within_tolerance = (
        calibrated_intervals.coverage_gap <= MAX_ACCEPTABLE_COVERAGE_GAP
    )
    substantial_improvement = gap_improvement >= MINIMUM_GAP_IMPROVEMENT

    width_to_mae_ratio = (
        calibrated_intervals.mean_interval_width / calibrated_regression.mae
        if calibrated_regression.mae > 0
        else float("inf")
    )
    width_practical = width_to_mae_ratio <= MAX_WIDTH_TO_MAE_RATIO

    mae_change = abs(calibrated_regression.mae - raw_regression.mae)
    rmse_change = abs(calibrated_regression.rmse - raw_regression.rmse)
    accuracy_preserved = (
        mae_change <= MAX_ALLOWED_MAE_CHANGE
        and rmse_change <= MAX_ALLOWED_RMSE_CHANGE
    )

    if (
        coverage_moved_closer
        and gap_within_tolerance
        and substantial_improvement
        and width_practical
        and accuracy_preserved
    ):
        result = "PASS"
        explanation = (
            "Calibration moved empirical coverage substantially closer to the "
            "90% target, the final coverage gap met tolerance, interval width "
            "remained within the declared practical threshold, and point-"
            "prediction accuracy was unchanged."
        )
    elif coverage_moved_closer and accuracy_preserved:
        result = "PARTIAL PASS"
        explanation = (
            "Calibration improved coverage and preserved point-prediction "
            "accuracy, but at least one declared coverage or interval-width "
            "criterion was not satisfied."
        )
    else:
        result = "FAIL"
        explanation = (
            "Calibration did not reliably improve target coverage under the "
            "declared criteria, or predictive accuracy was not preserved."
        )

    return ValidationDecision(
        overall_result=result,
        coverage_moved_closer=coverage_moved_closer,
        coverage_gap_within_tolerance=gap_within_tolerance,
        substantial_gap_improvement=substantial_improvement,
        interval_width_practical=width_practical,
        regression_accuracy_preserved=accuracy_preserved,
        explanation=explanation,
    )


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def save_coverage_figure(
    raw_metrics: IntervalMetrics,
    calibrated_metrics: IntervalMetrics,
    output_path: Path,
) -> None:
    labels = ["Raw interval", "Calibrated interval", "Target"]
    values = [
        raw_metrics.empirical_coverage,
        calibrated_metrics.empirical_coverage,
        TARGET_COVERAGE,
    ]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, values)
    plt.ylim(0.0, 1.0)
    plt.ylabel("Empirical coverage")
    plt.title("SUANR_V2 Test 02 — Coverage Before and After Calibration")
    plt.axhline(TARGET_COVERAGE, linestyle="--", linewidth=1.5)

    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            min(value + 0.025, 0.98),
            f"{value:.3f}",
            ha="center",
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def save_interval_width_figure(
    raw_widths: FloatArray,
    calibrated_widths: FloatArray,
    output_path: Path,
) -> None:
    plt.figure(figsize=(8, 5))
    plt.boxplot(
        [raw_widths, calibrated_widths],
        tick_labels=["Raw interval", "Calibrated interval"],
        showmeans=True,
    )
    plt.ylabel("Interval width")
    plt.title("SUANR_V2 Test 02 — Interval Width Comparison")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def save_prediction_interval_figure(
    evidence: pd.DataFrame,
    output_path: Path,
) -> None:
    ordered = evidence.sort_values("actual_target").reset_index(drop=True)
    x_values = np.arange(len(ordered))

    plt.figure(figsize=(12, 6))
    plt.fill_between(
        x_values,
        ordered["calibrated_lower"],
        ordered["calibrated_upper"],
        alpha=0.25,
        label="Calibrated 90% interval",
    )
    plt.plot(x_values, ordered["predicted_mean"], linewidth=1.5, label="Prediction")
    plt.scatter(x_values, ordered["actual_target"], s=18, label="Actual target")
    plt.xlabel("Test observations ordered by actual target")
    plt.ylabel("Diabetes disease-progression target")
    plt.title("SUANR_V2 Test 02 — Calibrated Prediction Intervals")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def print_metric_block(
    heading: str,
    interval_metrics: IntervalMetrics,
    regression_metrics: RegressionMetrics,
) -> None:
    print(f"\n{heading}")
    print("-" * len(heading))
    print(f"Empirical coverage:            {interval_metrics.empirical_coverage:.4f}")
    print(f"Coverage gap from 90%:         {interval_metrics.coverage_gap:.4f}")
    print(f"Mean interval width:           {interval_metrics.mean_interval_width:.4f}")
    print(f"Median interval width:         {interval_metrics.median_interval_width:.4f}")
    print(f"MAE:                           {regression_metrics.mae:.4f}")
    print(f"RMSE:                          {regression_metrics.rmse:.4f}")
    print(
        "Correlation(error, uncertainty): "
        f"{regression_metrics.uncertainty_error_correlation:.4f}"
    )
    print(
        "Correlation(error, entropy):     "
        f"{regression_metrics.entropy_error_correlation:.4f}"
    )


# =============================================================================
# COMPLETE VALIDATION TEST
# =============================================================================

def run_test() -> dict:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("=" * 79)
    print(TEST_NAME)
    print("=" * 79)
    print("Loading the scikit-learn diabetes regression dataset...")

    dataset = load_diabetes()
    X = np.asarray(dataset.data, dtype=float)
    y = np.asarray(dataset.target, dtype=float)
    original_indices = np.arange(len(y))

    # 60% train, 20% calibration, 20% final test.
    X_train, X_temp, y_train, y_temp, idx_train, idx_temp = train_test_split(
        X,
        y,
        original_indices,
        test_size=CALIBRATION_SIZE_FROM_FULL + TEST_SIZE_FROM_FULL,
        random_state=RANDOM_STATE,
    )
    X_calibration, X_test, y_calibration, y_test, idx_calibration, idx_test = (
        train_test_split(
            X_temp,
            y_temp,
            idx_temp,
            test_size=0.5,
            random_state=RANDOM_STATE,
        )
    )

    print(
        f"Dataset split: {len(y_train)} train / "
        f"{len(y_calibration)} calibration / {len(y_test)} test"
    )

    model = SUANR_V2(
        hidden_layer_sizes=HIDDEN_LAYER_SIZES,
        stochastic_noise=STOCHASTIC_NOISE,
        n_samples=N_STOCHASTIC_SAMPLES,
        lower_percentile=LOWER_PERCENTILE,
        upper_percentile=UPPER_PERCENTILE,
        entropy_bins=ENTROPY_BINS,
        random_state=RANDOM_STATE,
        max_iter=MAX_ITER,
    )

    print("Fitting SUANR_V2 on the training partition...")
    model.fit(X_train, y_train)

    print("Generating raw intervals for the calibration partition...")
    calibration_prediction = model.predict(X_calibration)

    calibration_scores = interval_nonconformity_scores(
        y_calibration,
        calibration_prediction.lower_bound,
        calibration_prediction.upper_bound,
    )
    q_hat, conformal_rank, adjusted_probability = finite_sample_conformal_quantile(
        calibration_scores,
        TARGET_COVERAGE,
    )

    print(f"Conformal expansion q_hat: {q_hat:.6f}")
    print(
        f"Finite-sample quantile: rank {conformal_rank}/{len(calibration_scores)} "
        f"(probability {adjusted_probability:.6f})"
    )

    print("Evaluating untouched final test partition...")
    test_prediction = model.predict(X_test)

    raw_lower = test_prediction.lower_bound
    raw_upper = test_prediction.upper_bound
    calibrated_lower = raw_lower - q_hat
    calibrated_upper = raw_upper + q_hat

    raw_interval_metrics = calculate_interval_metrics(
        y_test,
        raw_lower,
        raw_upper,
        TARGET_COVERAGE,
    )
    calibrated_interval_metrics = calculate_interval_metrics(
        y_test,
        calibrated_lower,
        calibrated_upper,
        TARGET_COVERAGE,
    )

    # Calibration changes interval bounds only. Point predictions, uncertainty
    # standard deviations, entropy values, MAE, and RMSE remain identical.
    raw_regression_metrics = calculate_regression_metrics(y_test, test_prediction)
    calibrated_regression_metrics = calculate_regression_metrics(
        y_test,
        test_prediction,
    )

    decision = make_validation_decision(
        raw_interval_metrics,
        calibrated_interval_metrics,
        raw_regression_metrics,
        calibrated_regression_metrics,
    )

    raw_covered = (y_test >= raw_lower) & (y_test <= raw_upper)
    calibrated_covered = (y_test >= calibrated_lower) & (y_test <= calibrated_upper)
    absolute_error = np.abs(y_test - test_prediction.mean)

    evidence = pd.DataFrame(
        {
            "dataset_index": idx_test,
            "actual_target": y_test,
            "predicted_mean": test_prediction.mean,
            "absolute_error": absolute_error,
            "uncertainty_std": test_prediction.uncertainty_std,
            "entropy": test_prediction.entropy,
            "raw_lower": raw_lower,
            "raw_upper": raw_upper,
            "raw_width": raw_upper - raw_lower,
            "raw_covered": raw_covered,
            "calibrated_lower": calibrated_lower,
            "calibrated_upper": calibrated_upper,
            "calibrated_width": calibrated_upper - calibrated_lower,
            "calibrated_covered": calibrated_covered,
        }
    ).sort_values("dataset_index")

    calibration_evidence = pd.DataFrame(
        {
            "dataset_index": idx_calibration,
            "actual_target": y_calibration,
            "raw_lower": calibration_prediction.lower_bound,
            "raw_upper": calibration_prediction.upper_bound,
            "nonconformity_score": calibration_scores,
        }
    ).sort_values("dataset_index")

    width_to_mae_ratio = (
        calibrated_interval_metrics.mean_interval_width
        / calibrated_regression_metrics.mae
    )
    coverage_gap_improvement = (
        raw_interval_metrics.coverage_gap
        - calibrated_interval_metrics.coverage_gap
    )

    summary = {
        "test": {
            "name": TEST_NAME,
            "project": "SUANR_V2",
            "author": "Martin Pitre",
            "created": "2026-07-27",
            "dataset": "scikit-learn diabetes dataset",
            "calibration_method": "split conformal additive interval expansion",
            "target_coverage": TARGET_COVERAGE,
            "alpha": ALPHA,
            "random_state": RANDOM_STATE,
        },
        "dataset_split": {
            "total_observations": int(len(y)),
            "training_observations": int(len(y_train)),
            "calibration_observations": int(len(y_calibration)),
            "test_observations": int(len(y_test)),
        },
        "model_configuration": {
            "hidden_layer_sizes": list(HIDDEN_LAYER_SIZES),
            "stochastic_noise": STOCHASTIC_NOISE,
            "n_stochastic_samples": N_STOCHASTIC_SAMPLES,
            "lower_percentile": LOWER_PERCENTILE,
            "upper_percentile": UPPER_PERCENTILE,
            "entropy_bins": ENTROPY_BINS,
            "max_iter": MAX_ITER,
        },
        "calibration": {
            "q_hat": q_hat,
            "conformal_rank": conformal_rank,
            "adjusted_quantile_probability": adjusted_probability,
            "zero_score_count": int(np.sum(np.isclose(calibration_scores, 0.0))),
            "positive_score_count": int(np.sum(calibration_scores > 0.0)),
        },
        "raw_test_metrics": {
            **asdict(raw_interval_metrics),
            **asdict(raw_regression_metrics),
        },
        "calibrated_test_metrics": {
            **asdict(calibrated_interval_metrics),
            **asdict(calibrated_regression_metrics),
        },
        "comparison": {
            "coverage_gap_improvement": coverage_gap_improvement,
            "mean_width_increase": (
                calibrated_interval_metrics.mean_interval_width
                - raw_interval_metrics.mean_interval_width
            ),
            "mean_width_multiplier": (
                calibrated_interval_metrics.mean_interval_width
                / raw_interval_metrics.mean_interval_width
                if raw_interval_metrics.mean_interval_width > 0
                else float("inf")
            ),
            "calibrated_width_to_mae_ratio": width_to_mae_ratio,
            "mae_change": (
                calibrated_regression_metrics.mae - raw_regression_metrics.mae
            ),
            "rmse_change": (
                calibrated_regression_metrics.rmse - raw_regression_metrics.rmse
            ),
        },
        "success_thresholds": {
            "maximum_acceptable_coverage_gap": MAX_ACCEPTABLE_COVERAGE_GAP,
            "minimum_gap_improvement": MINIMUM_GAP_IMPROVEMENT,
            "maximum_width_to_mae_ratio": MAX_WIDTH_TO_MAE_RATIO,
            "maximum_allowed_mae_change": MAX_ALLOWED_MAE_CHANGE,
            "maximum_allowed_rmse_change": MAX_ALLOWED_RMSE_CHANGE,
        },
        "validation_decision": asdict(decision),
        "software_environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "scientific_boundary": (
            "The result applies to this fixed dataset, split, seed, model "
            "configuration, and calibration strategy. Broader reliability "
            "claims require repeated-seed and external-dataset validation."
        ),
    }

    evidence_path = OUTPUT_DIRECTORY / "SUANR_V2_Test_02_Evidence.csv"
    calibration_path = OUTPUT_DIRECTORY / "SUANR_V2_Test_02_Calibration_Evidence.csv"
    summary_path = OUTPUT_DIRECTORY / "SUANR_V2_Test_02_Summary.json"
    report_path = OUTPUT_DIRECTORY / "SUANR_V2_Test_02_Validation_Report.txt"

    evidence.to_csv(evidence_path, index=False)
    calibration_evidence.to_csv(calibration_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    save_coverage_figure(
        raw_interval_metrics,
        calibrated_interval_metrics,
        OUTPUT_DIRECTORY / "SUANR_V2_Test_02_Coverage.png",
    )
    save_interval_width_figure(
        np.asarray(raw_upper - raw_lower, dtype=float),
        np.asarray(calibrated_upper - calibrated_lower, dtype=float),
        OUTPUT_DIRECTORY / "SUANR_V2_Test_02_Interval_Widths.png",
    )
    save_prediction_interval_figure(
        evidence,
        OUTPUT_DIRECTORY / "SUANR_V2_Test_02_Prediction_Intervals.png",
    )

    print_metric_block(
        "RAW SUANR_V2 TEST INTERVALS",
        raw_interval_metrics,
        raw_regression_metrics,
    )
    print_metric_block(
        "CALIBRATED SUANR_V2 TEST INTERVALS",
        calibrated_interval_metrics,
        calibrated_regression_metrics,
    )

    print("\nVALIDATION CHECKS")
    print("-----------------")
    print(f"Coverage moved closer:         {decision.coverage_moved_closer}")
    print(f"Coverage gap within tolerance: {decision.coverage_gap_within_tolerance}")
    print(f"Substantial gap improvement:   {decision.substantial_gap_improvement}")
    print(f"Interval width practical:      {decision.interval_width_practical}")
    print(f"Regression accuracy preserved: {decision.regression_accuracy_preserved}")
    print(f"Width-to-MAE ratio:            {width_to_mae_ratio:.4f}")

    report_lines = [
        TEST_NAME,
        "=" * len(TEST_NAME),
        "",
        f"Dataset: scikit-learn diabetes dataset",
        (
            f"Split: {len(y_train)} training / {len(y_calibration)} calibration / "
            f"{len(y_test)} testing"
        ),
        f"Target coverage: {TARGET_COVERAGE:.2%}",
        f"Calibration method: split conformal additive interval expansion",
        f"Conformal q_hat: {q_hat:.6f}",
        "",
        "Raw intervals:",
        f"  Empirical coverage: {raw_interval_metrics.empirical_coverage:.4f}",
        f"  Coverage gap: {raw_interval_metrics.coverage_gap:.4f}",
        f"  Mean width: {raw_interval_metrics.mean_interval_width:.4f}",
        f"  Median width: {raw_interval_metrics.median_interval_width:.4f}",
        "",
        "Calibrated intervals:",
        (
            f"  Empirical coverage: "
            f"{calibrated_interval_metrics.empirical_coverage:.4f}"
        ),
        f"  Coverage gap: {calibrated_interval_metrics.coverage_gap:.4f}",
        f"  Mean width: {calibrated_interval_metrics.mean_interval_width:.4f}",
        f"  Median width: {calibrated_interval_metrics.median_interval_width:.4f}",
        "",
        "Regression accuracy:",
        f"  MAE: {calibrated_regression_metrics.mae:.4f}",
        f"  RMSE: {calibrated_regression_metrics.rmse:.4f}",
        (
            "  Correlation(error, uncertainty): "
            f"{calibrated_regression_metrics.uncertainty_error_correlation:.4f}"
        ),
        (
            "  Correlation(error, entropy): "
            f"{calibrated_regression_metrics.entropy_error_correlation:.4f}"
        ),
        "",
        f"OVERALL RESULT: {decision.overall_result}",
        decision.explanation,
        "",
        "Scientific boundary:",
        summary["scientific_boundary"],
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print("\n" + "=" * 79)
    print(f"OVERALL RESULT: {decision.overall_result}")
    print(decision.explanation)
    print("=" * 79)
    print(f"\nEvidence files saved in: {OUTPUT_DIRECTORY.resolve()}")
    for file_path in sorted(OUTPUT_DIRECTORY.iterdir()):
        print(f"  - {file_path.name}")

    # In Google Colab, automatically create one downloadable ZIP archive.
    try:
        from google.colab import files  # type: ignore
        import shutil

        zip_path = shutil.make_archive(
            "SUANR_V2_Test_02_Results",
            "zip",
            root_dir=OUTPUT_DIRECTORY,
        )
        print(f"\nGoogle Colab archive created: {zip_path}")
        files.download(zip_path)
    except ImportError:
        pass

    return summary


if __name__ == "__main__":
    TEST_SUMMARY = run_test()
