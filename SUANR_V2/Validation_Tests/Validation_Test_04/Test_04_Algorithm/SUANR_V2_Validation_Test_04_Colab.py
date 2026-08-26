"""
SUANR_V2 Validation Test 04 — Cross-Dataset Generalization
Standalone Google Colab Edition

Author: Martin Pitre
Created: 27 July 2026
Status: Phase 1 completion validation protocol

HOW TO USE IN GOOGLE COLAB
--------------------------
1. Open a new Google Colab notebook.
2. Copy this entire file into one code cell.
3. Press Run.
4. Download the generated ZIP evidence package from the Files panel.

The program evaluates:
- scikit-learn Diabetes (control)
- California Housing
- Friedman #1 synthetic regression

Outputs:
- CSV execution results
- JSON summary
- Publication-quality figures
- Plain-text execution record
- ZIP evidence package
"""

from __future__ import annotations

import json
import math
import platform
import sys
import time
import warnings
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.datasets import fetch_california_housing, load_diabetes, make_friedman1
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# =============================================================================
# USER-EDITABLE CONFIGURATION
# =============================================================================
RANDOM_SEED = 42
NOMINAL_COVERAGE = 0.90
ENSEMBLE_MEMBERS = 12
MAX_ITERATIONS = 700
TEST_FRACTION = 0.20
CALIBRATION_FRACTION_OF_REMAINDER = 0.25  # gives 60/20/20 overall
CALIFORNIA_MAX_SAMPLES = 6000             # limits runtime in Colab
FRIEDMAN_SAMPLES = 3000
OUTPUT_DIRECTORY = Path("SUANR_V2_Test_04_Output")

# Acceptance criteria from the Test 04 protocol.
COVERAGE_MIN = 0.85
COVERAGE_MAX = 0.95
MAX_ABSOLUTE_CALIBRATION_ERROR = 0.05


@dataclass
class DatasetResult:
    dataset: str
    n_samples: int
    n_features: int
    train_samples: int
    calibration_samples: int
    test_samples: int
    mae: float
    rmse: float
    r2: float
    raw_coverage: float
    raw_mean_interval_width: float
    calibrated_coverage: float
    calibrated_mean_interval_width: float
    calibrated_median_interval_width: float
    calibration_error: float
    conformal_q_hat: float
    uncertainty_error_correlation: float
    execution_seconds: float
    coverage_pass: bool
    calibration_error_pass: bool
    execution_pass: bool
    overall_pass: bool
    notes: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def finite_sample_conformal_quantile(scores: np.ndarray, coverage: float) -> Tuple[float, int, float]:
    """Return split-conformal finite-sample quantile and audit details."""
    scores = np.asarray(scores, dtype=float)
    n = len(scores)
    if n == 0:
        raise ValueError("Calibration score array is empty.")

    rank = int(math.ceil((n + 1) * coverage))
    rank = min(max(rank, 1), n)
    probability = rank / n
    q_hat = float(np.partition(scores, rank - 1)[rank - 1])
    return q_hat, rank, probability


def safe_correlation(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def load_datasets(seed: int) -> List[Tuple[str, np.ndarray, np.ndarray, str]]:
    datasets: List[Tuple[str, np.ndarray, np.ndarray, str]] = []

    diabetes = load_diabetes()
    datasets.append(
        ("Diabetes", diabetes.data.astype(float), diabetes.target.astype(float), "Built-in control dataset")
    )

    try:
        california = fetch_california_housing()
        x_cal = california.data.astype(float)
        y_cal = california.target.astype(float)
        note = "California Housing loaded successfully"

        if CALIFORNIA_MAX_SAMPLES and len(y_cal) > CALIFORNIA_MAX_SAMPLES:
            rng = np.random.default_rng(seed)
            idx = rng.choice(len(y_cal), size=CALIFORNIA_MAX_SAMPLES, replace=False)
            x_cal = x_cal[idx]
            y_cal = y_cal[idx]
            note += f"; deterministic subsample of {CALIFORNIA_MAX_SAMPLES} used"

        datasets.append(("California Housing", x_cal, y_cal, note))
    except Exception as exc:
        # A failed network fetch should be recorded rather than silently replacing the dataset.
        datasets.append(("California Housing", np.empty((0, 0)), np.empty((0,)), f"LOAD FAILURE: {exc}"))

    x_f, y_f = make_friedman1(
        n_samples=FRIEDMAN_SAMPLES,
        n_features=10,
        noise=1.0,
        random_state=seed,
    )
    datasets.append(("Friedman #1", x_f.astype(float), y_f.astype(float), "Synthetic nonlinear regression dataset"))

    return datasets


def build_ensemble(seed: int) -> List[Pipeline]:
    models: List[Pipeline] = []
    for member in range(ENSEMBLE_MEMBERS):
        model = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "mlp",
                    MLPRegressor(
                        hidden_layer_sizes=(64, 32),
                        activation="relu",
                        solver="adam",
                        alpha=1e-4,
                        learning_rate_init=1e-3,
                        max_iter=MAX_ITERATIONS,
                        early_stopping=True,
                        validation_fraction=0.15,
                        n_iter_no_change=35,
                        random_state=seed + member,
                    ),
                ),
            ]
        )
        models.append(model)
    return models


def ensemble_predict(models: List[Pipeline], x: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    predictions = np.vstack([model.predict(x) for model in models])
    mean_prediction = predictions.mean(axis=0)
    epistemic_std = predictions.std(axis=0, ddof=1) if len(models) > 1 else np.zeros(len(x))
    return mean_prediction, epistemic_std, predictions


def evaluate_dataset(name: str, x: np.ndarray, y: np.ndarray, load_note: str) -> Tuple[DatasetResult, pd.DataFrame]:
    start = time.perf_counter()

    if x.size == 0 or y.size == 0:
        result = DatasetResult(
            dataset=name,
            n_samples=0,
            n_features=0,
            train_samples=0,
            calibration_samples=0,
            test_samples=0,
            mae=float("nan"),
            rmse=float("nan"),
            r2=float("nan"),
            raw_coverage=float("nan"),
            raw_mean_interval_width=float("nan"),
            calibrated_coverage=float("nan"),
            calibrated_mean_interval_width=float("nan"),
            calibrated_median_interval_width=float("nan"),
            calibration_error=float("nan"),
            conformal_q_hat=float("nan"),
            uncertainty_error_correlation=float("nan"),
            execution_seconds=time.perf_counter() - start,
            coverage_pass=False,
            calibration_error_pass=False,
            execution_pass=False,
            overall_pass=False,
            notes=load_note,
        )
        return result, pd.DataFrame()

    x_train_cal, x_test, y_train_cal, y_test = train_test_split(
        x, y, test_size=TEST_FRACTION, random_state=RANDOM_SEED
    )
    x_train, x_cal, y_train, y_cal = train_test_split(
        x_train_cal,
        y_train_cal,
        test_size=CALIBRATION_FRACTION_OF_REMAINDER,
        random_state=RANDOM_SEED + 1,
    )

    models = build_ensemble(RANDOM_SEED)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        for model in models:
            model.fit(x_train, y_train)

    cal_mean, cal_std, _ = ensemble_predict(models, x_cal)
    test_mean, test_std, _ = ensemble_predict(models, x_test)

    # Raw central interval based on the empirical ensemble distribution.
    alpha = 1.0 - NOMINAL_COVERAGE
    lower_percentile = 100.0 * alpha / 2.0
    upper_percentile = 100.0 * (1.0 - alpha / 2.0)

    cal_member_predictions = np.vstack([model.predict(x_cal) for model in models])
    test_member_predictions = np.vstack([model.predict(x_test) for model in models])

    cal_raw_lower = np.percentile(cal_member_predictions, lower_percentile, axis=0)
    cal_raw_upper = np.percentile(cal_member_predictions, upper_percentile, axis=0)
    test_raw_lower = np.percentile(test_member_predictions, lower_percentile, axis=0)
    test_raw_upper = np.percentile(test_member_predictions, upper_percentile, axis=0)

    # Conformal score expands whichever side of the raw interval misses the target.
    cal_scores = np.maximum.reduce(
        [cal_raw_lower - y_cal, y_cal - cal_raw_upper, np.zeros_like(y_cal)]
    )
    q_hat, rank, quantile_probability = finite_sample_conformal_quantile(
        cal_scores, NOMINAL_COVERAGE
    )

    calibrated_lower = test_raw_lower - q_hat
    calibrated_upper = test_raw_upper + q_hat

    abs_error = np.abs(y_test - test_mean)
    raw_covered = (y_test >= test_raw_lower) & (y_test <= test_raw_upper)
    calibrated_covered = (y_test >= calibrated_lower) & (y_test <= calibrated_upper)

    mae = float(mean_absolute_error(y_test, test_mean))
    rmse = float(np.sqrt(mean_squared_error(y_test, test_mean)))
    r2 = float(r2_score(y_test, test_mean))
    raw_coverage = float(np.mean(raw_covered))
    calibrated_coverage = float(np.mean(calibrated_covered))
    raw_width = test_raw_upper - test_raw_lower
    calibrated_width = calibrated_upper - calibrated_lower
    calibration_error = calibrated_coverage - NOMINAL_COVERAGE
    uncertainty_corr = safe_correlation(abs_error, test_std)

    coverage_pass = COVERAGE_MIN <= calibrated_coverage <= COVERAGE_MAX
    calibration_error_pass = abs(calibration_error) <= MAX_ABSOLUTE_CALIBRATION_ERROR
    execution_pass = True
    overall_pass = coverage_pass and calibration_error_pass and execution_pass

    elapsed = time.perf_counter() - start
    notes = (
        f"{load_note}; conformal rank {rank}/{len(cal_scores)} "
        f"(probability={quantile_probability:.6f})"
    )

    result = DatasetResult(
        dataset=name,
        n_samples=int(len(y)),
        n_features=int(x.shape[1]),
        train_samples=int(len(y_train)),
        calibration_samples=int(len(y_cal)),
        test_samples=int(len(y_test)),
        mae=mae,
        rmse=rmse,
        r2=r2,
        raw_coverage=raw_coverage,
        raw_mean_interval_width=float(np.mean(raw_width)),
        calibrated_coverage=calibrated_coverage,
        calibrated_mean_interval_width=float(np.mean(calibrated_width)),
        calibrated_median_interval_width=float(np.median(calibrated_width)),
        calibration_error=calibration_error,
        conformal_q_hat=q_hat,
        uncertainty_error_correlation=uncertainty_corr,
        execution_seconds=float(elapsed),
        coverage_pass=coverage_pass,
        calibration_error_pass=calibration_error_pass,
        execution_pass=execution_pass,
        overall_pass=overall_pass,
        notes=notes,
    )

    detail = pd.DataFrame(
        {
            "dataset": name,
            "actual": y_test,
            "prediction": test_mean,
            "absolute_error": abs_error,
            "ensemble_uncertainty_std": test_std,
            "raw_lower": test_raw_lower,
            "raw_upper": test_raw_upper,
            "raw_covered": raw_covered,
            "calibrated_lower": calibrated_lower,
            "calibrated_upper": calibrated_upper,
            "calibrated_covered": calibrated_covered,
        }
    )
    return result, detail


def create_figures(results_df: pd.DataFrame, details: Dict[str, pd.DataFrame], output_dir: Path) -> List[Path]:
    figure_paths: List[Path] = []

    # Figure 1: calibrated coverage by dataset.
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(results_df["dataset"], results_df["calibrated_coverage"])
    ax.axhline(NOMINAL_COVERAGE, linestyle="--", label="Nominal 90%")
    ax.axhspan(COVERAGE_MIN, COVERAGE_MAX, alpha=0.15, label="Acceptance range 85%–95%")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Empirical coverage")
    ax.set_title("SUANR_V2 Test 04 — Calibrated Coverage Across Datasets")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = output_dir / "Figure_01_Calibrated_Coverage.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figure_paths.append(path)

    # Figure 2: accuracy metrics.
    fig, ax = plt.subplots(figsize=(10, 6))
    positions = np.arange(len(results_df))
    width = 0.36
    ax.bar(positions - width / 2, results_df["mae"], width, label="MAE")
    ax.bar(positions + width / 2, results_df["rmse"], width, label="RMSE")
    ax.set_xticks(positions)
    ax.set_xticklabels(results_df["dataset"])
    ax.set_ylabel("Error")
    ax.set_title("SUANR_V2 Test 04 — Prediction Accuracy")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = output_dir / "Figure_02_Accuracy_Metrics.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figure_paths.append(path)

    # Figure 3: interval width before and after calibration.
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(positions - width / 2, results_df["raw_mean_interval_width"], width, label="Raw")
    ax.bar(positions + width / 2, results_df["calibrated_mean_interval_width"], width, label="Calibrated")
    ax.set_xticks(positions)
    ax.set_xticklabels(results_df["dataset"])
    ax.set_ylabel("Mean interval width")
    ax.set_title("SUANR_V2 Test 04 — Raw vs Calibrated Interval Width")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = output_dir / "Figure_03_Interval_Width.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figure_paths.append(path)

    # One interval plot per successful dataset.
    for dataset_name, detail in details.items():
        if detail.empty:
            continue
        shown = detail.sort_values("actual").reset_index(drop=True).head(120)
        x_axis = np.arange(len(shown))
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.fill_between(
            x_axis,
            shown["calibrated_lower"],
            shown["calibrated_upper"],
            alpha=0.25,
            label="90% calibrated interval",
        )
        ax.plot(x_axis, shown["actual"], marker="o", markersize=3, linewidth=1, label="Actual")
        ax.plot(x_axis, shown["prediction"], linewidth=1.5, label="Prediction")
        ax.set_xlabel("Sorted test observations (up to 120 shown)")
        ax.set_ylabel("Target value")
        ax.set_title(f"{dataset_name} — Predictions and Calibrated Intervals")
        ax.legend()
        ax.grid(alpha=0.2)
        fig.tight_layout()
        safe_name = dataset_name.replace(" ", "_").replace("#", "")
        path = output_dir / f"Figure_Interval_{safe_name}.png"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        plt.close(fig)
        figure_paths.append(path)

    return figure_paths


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return None if not math.isfinite(value) else value
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def write_execution_record(results: List[DatasetResult], overall_pass: bool, output_dir: Path) -> Path:
    lines = [
        "SUANR_V2 VALIDATION TEST 04 — EXECUTION RECORD",
        "=" * 72,
        f"UTC timestamp: {utc_now_iso()}",
        f"Python: {sys.version.split()[0]}",
        f"Platform: {platform.platform()}",
        f"Nominal coverage: {NOMINAL_COVERAGE:.0%}",
        f"Ensemble members: {ENSEMBLE_MEMBERS}",
        "",
    ]

    for r in results:
        lines.extend(
            [
                r.dataset.upper(),
                "-" * len(r.dataset),
                f"Samples: {r.n_samples} | Features: {r.n_features}",
                f"Split: {r.train_samples} train / {r.calibration_samples} calibration / {r.test_samples} test",
                f"MAE: {r.mae:.6f}" if math.isfinite(r.mae) else "MAE: unavailable",
                f"RMSE: {r.rmse:.6f}" if math.isfinite(r.rmse) else "RMSE: unavailable",
                f"R²: {r.r2:.6f}" if math.isfinite(r.r2) else "R²: unavailable",
                f"Raw coverage: {r.raw_coverage:.4f}" if math.isfinite(r.raw_coverage) else "Raw coverage: unavailable",
                f"Calibrated coverage: {r.calibrated_coverage:.4f}" if math.isfinite(r.calibrated_coverage) else "Calibrated coverage: unavailable",
                f"Calibration error: {r.calibration_error:+.4f}" if math.isfinite(r.calibration_error) else "Calibration error: unavailable",
                f"Mean calibrated interval width: {r.calibrated_mean_interval_width:.6f}" if math.isfinite(r.calibrated_mean_interval_width) else "Mean calibrated interval width: unavailable",
                f"Conformal q_hat: {r.conformal_q_hat:.6f}" if math.isfinite(r.conformal_q_hat) else "Conformal q_hat: unavailable",
                f"Corr(|error|, uncertainty): {r.uncertainty_error_correlation:.6f}" if math.isfinite(r.uncertainty_error_correlation) else "Corr(|error|, uncertainty): unavailable",
                f"Execution time: {r.execution_seconds:.2f} seconds",
                f"Coverage criterion: {'PASS' if r.coverage_pass else 'FAIL'}",
                f"Calibration-error criterion: {'PASS' if r.calibration_error_pass else 'FAIL'}",
                f"Dataset result: {'PASS' if r.overall_pass else 'FAIL'}",
                f"Notes: {r.notes}",
                "",
            ]
        )

    lines.extend(
        [
            "PHASE 1 COMPLETION DECISION",
            "-" * 29,
            f"OVERALL TEST RESULT: {'PASS' if overall_pass else 'FAIL'}",
            (
                "Phase 1 completion supported: all datasets executed and met the coverage and calibration criteria."
                if overall_pass
                else "Phase 1 completion not yet supported: at least one dataset failed execution or an acceptance criterion."
            ),
        ]
    )

    path = output_dir / "SUANR_V2_Test_04_Execution_Record.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    print("=" * 79)
    print("SUANR_V2 Validation Test 04 — Cross-Dataset Generalization")
    print("=" * 79)
    print(f"Nominal interval coverage: {NOMINAL_COVERAGE:.0%}")
    print(f"Ensemble members: {ENSEMBLE_MEMBERS}")
    print(f"Output directory: {OUTPUT_DIRECTORY.resolve()}")
    print()

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    all_results: List[DatasetResult] = []
    all_details: Dict[str, pd.DataFrame] = {}

    for name, x, y, note in load_datasets(RANDOM_SEED):
        print(f"Running {name}...")
        try:
            result, detail = evaluate_dataset(name, x, y, note)
        except Exception as exc:
            result = DatasetResult(
                dataset=name,
                n_samples=int(len(y)) if y is not None else 0,
                n_features=int(x.shape[1]) if getattr(x, "ndim", 0) == 2 else 0,
                train_samples=0,
                calibration_samples=0,
                test_samples=0,
                mae=float("nan"), rmse=float("nan"), r2=float("nan"),
                raw_coverage=float("nan"), raw_mean_interval_width=float("nan"),
                calibrated_coverage=float("nan"), calibrated_mean_interval_width=float("nan"),
                calibrated_median_interval_width=float("nan"), calibration_error=float("nan"),
                conformal_q_hat=float("nan"), uncertainty_error_correlation=float("nan"),
                execution_seconds=0.0, coverage_pass=False, calibration_error_pass=False,
                execution_pass=False, overall_pass=False, notes=f"EXECUTION FAILURE: {exc}",
            )
            detail = pd.DataFrame()

        all_results.append(result)
        all_details[name] = detail

        if result.execution_pass:
            print(
                f"  MAE={result.mae:.4f} | RMSE={result.rmse:.4f} | "
                f"coverage={result.calibrated_coverage:.4f} | "
                f"calibration error={result.calibration_error:+.4f} | "
                f"{'PASS' if result.overall_pass else 'FAIL'}"
            )
        else:
            print(f"  FAIL — {result.notes}")
        print()

    results_df = pd.DataFrame([asdict(r) for r in all_results])
    results_csv = OUTPUT_DIRECTORY / "SUANR_V2_Test_04_Dataset_Summary.csv"
    results_df.to_csv(results_csv, index=False)

    detail_csv_paths: List[Path] = []
    for dataset_name, detail in all_details.items():
        if detail.empty:
            continue
        safe_name = dataset_name.replace(" ", "_").replace("#", "")
        path = OUTPUT_DIRECTORY / f"SUANR_V2_Test_04_{safe_name}_Predictions.csv"
        detail.to_csv(path, index=False)
        detail_csv_paths.append(path)

    successful_results = results_df[results_df["execution_pass"] == True].copy()  # noqa: E712
    figure_paths = create_figures(successful_results, all_details, OUTPUT_DIRECTORY) if not successful_results.empty else []

    overall_pass = bool(all(r.overall_pass for r in all_results))
    execution_record = write_execution_record(all_results, overall_pass, OUTPUT_DIRECTORY)

    summary = {
        "test": "SUANR_V2 Validation Test 04",
        "purpose": "Cross-dataset generalization and Phase 1 completion",
        "created_utc": utc_now_iso(),
        "configuration": {
            "random_seed": RANDOM_SEED,
            "nominal_coverage": NOMINAL_COVERAGE,
            "ensemble_members": ENSEMBLE_MEMBERS,
            "max_iterations": MAX_ITERATIONS,
            "test_fraction": TEST_FRACTION,
            "calibration_fraction_of_remainder": CALIBRATION_FRACTION_OF_REMAINDER,
            "california_max_samples": CALIFORNIA_MAX_SAMPLES,
            "friedman_samples": FRIEDMAN_SAMPLES,
        },
        "acceptance_criteria": {
            "coverage_range": [COVERAGE_MIN, COVERAGE_MAX],
            "maximum_absolute_calibration_error": MAX_ABSOLUTE_CALIBRATION_ERROR,
            "successful_execution_required_for_every_dataset": True,
        },
        "dataset_results": [asdict(r) for r in all_results],
        "overall_pass": overall_pass,
        "phase_1_completion_supported": overall_pass,
        "phase_2_next_test": "SUANR_V2 vs. XGBoost Comparative Evaluation",
    }
    summary_json = OUTPUT_DIRECTORY / "SUANR_V2_Test_04_Summary.json"
    summary_json.write_text(json.dumps(json_safe(summary), indent=2), encoding="utf-8")

    zip_path = Path("SUANR_V2_Validation_Test_04_Evidence_Package.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT_DIRECTORY.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(OUTPUT_DIRECTORY.parent))

    print("=" * 79)
    print(f"OVERALL RESULT: {'PASS' if overall_pass else 'FAIL'}")
    print(
        "PHASE 1 COMPLETION: SUPPORTED"
        if overall_pass
        else "PHASE 1 COMPLETION: NOT YET SUPPORTED"
    )
    print("=" * 79)
    print(f"CSV summary: {results_csv}")
    print(f"JSON summary: {summary_json}")
    print(f"Execution record: {execution_record}")
    print(f"Evidence package: {zip_path.resolve()}")

    # In Google Colab, offer an automatic download of the ZIP.
    try:
        from google.colab import files  # type: ignore
        print("\nStarting download of the evidence package...")
        files.download(str(zip_path))
    except Exception:
        print("\nNot running in Google Colab; automatic download skipped.")


if __name__ == "__main__":
    main()
