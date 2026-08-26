"""SUANR_V2 Validation Test 03 — repeated-split calibration stability.

100% Google Colab compatible.

Run directly in a Colab cell:
    %run SUANR_V2_Test_03_Colab.py

Run as a script:
    !python SUANR_V2_Test_03_Colab.py

Optional settings:
    !python SUANR_V2_Test_03_Colab.py --runs 3 --ensemble-members 4
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import warnings
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.stats import t
import sklearn
from sklearn.datasets import load_diabetes
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TARGET = 0.90
ALPHA = 0.10
EPS = 1e-12


@dataclass(frozen=True)
class Config:
    runs: int = 30
    ensemble_members: int = 8
    base_seed: int = 20260727
    max_iter: int = 1200
    output_dir: str = "."
    auto_download: bool = False


def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or np.std(a) <= EPS or np.std(b) <= EPS:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def model(seed, c):
    return Pipeline([
        ("scale", StandardScaler()),
        ("mlp", MLPRegressor(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            learning_rate_init=1e-3,
            max_iter=c.max_iter,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=35,
            random_state=seed,
        )),
    ])


def ensemble(xtr, ytr, xe, seed, c):
    rng = np.random.default_rng(seed)
    preds = []
    for m in range(c.ensemble_members):
        idx = rng.integers(0, len(xtr), len(xtr))
        reg = model((seed * 1000 + m) % (2**32 - 1), c)
        reg.fit(xtr[idx], ytr[idx])
        preds.append(reg.predict(xe))
    return np.vstack(preds)


def describe(preds):
    sd = np.std(preds, axis=0, ddof=1)
    return {
        "mean": np.mean(preds, axis=0),
        "sd": sd,
        "entropy": 0.5 * np.log(2 * np.pi * np.e * np.maximum(sd, EPS) ** 2),
        "lo": np.quantile(preds, ALPHA / 2, axis=0),
        "hi": np.quantile(preds, 1 - ALPHA / 2, axis=0),
    }


def qhat(y, lo, hi):
    scores = np.maximum.reduce([lo - y, y - hi, np.zeros_like(y)])
    n = len(scores)
    rank = min(math.ceil((n + 1) * (1 - ALPHA)), n)
    return float(np.sort(scores)[rank - 1]), int(rank), float(rank / n)


def imetrics(y, lo, hi):
    w = hi - lo
    return {
        "coverage": float(np.mean((y >= lo) & (y <= hi))),
        "mean_width": float(np.mean(w)),
        "median_width": float(np.median(w)),
        "min_width": float(np.min(w)),
        "max_width": float(np.max(w)),
        "valid": bool(
            np.isfinite(lo).all()
            and np.isfinite(hi).all()
            and (lo <= hi).all()
        ),
    }


def one_run(x, y, run, seed, c):
    xd, xt, yd, yt = train_test_split(
        x, y, test_size=0.20, random_state=seed
    )
    xtr, xc, ytr, yc = train_test_split(
        xd, yd, test_size=0.25, random_state=seed + 1
    )

    p = ensemble(xtr, ytr, np.vstack([xc, xt]), seed, c)
    dc = describe(p[:, :len(xc)])
    dt = describe(p[:, len(xc):])

    q, rank, prob = qhat(yc, dc["lo"], dc["hi"])
    clo, chi = dt["lo"] - q, dt["hi"] + q

    raw = imetrics(yt, dt["lo"], dt["hi"])
    cal = imetrics(yt, clo, chi)
    err = np.abs(yt - dt["mean"])

    return {
        "run": run,
        "seed": seed,
        "train_size": len(xtr),
        "calibration_size": len(xc),
        "test_size": len(xt),
        "mae": float(mean_absolute_error(yt, dt["mean"])),
        "rmse": float(np.sqrt(mean_squared_error(yt, dt["mean"]))),
        "raw_coverage": raw["coverage"],
        "raw_coverage_gap": abs(raw["coverage"] - TARGET),
        "raw_mean_width": raw["mean_width"],
        "raw_median_width": raw["median_width"],
        "raw_min_width": raw["min_width"],
        "raw_max_width": raw["max_width"],
        "calibrated_coverage": cal["coverage"],
        "calibrated_coverage_gap": abs(cal["coverage"] - TARGET),
        "calibrated_mean_width": cal["mean_width"],
        "calibrated_median_width": cal["median_width"],
        "calibrated_min_width": cal["min_width"],
        "calibrated_max_width": cal["max_width"],
        "coverage_improvement": cal["coverage"] - raw["coverage"],
        "width_increase": cal["mean_width"] - raw["mean_width"],
        "width_ratio": (
            cal["mean_width"] / raw["mean_width"]
            if raw["mean_width"] > EPS
            else float("nan")
        ),
        "q_hat": q,
        "quantile_rank": rank,
        "quantile_probability": prob,
        "mean_uncertainty": float(np.mean(dt["sd"])),
        "mean_entropy": float(np.mean(dt["entropy"])),
        "error_uncertainty_correlation": corr(err, dt["sd"]),
        "error_entropy_correlation": corr(err, dt["entropy"]),
        "raw_intervals_valid": raw["valid"],
        "calibrated_intervals_valid": cal["valid"],
        "run_status": "SUCCESS",
        "error_message": "",
    }


def stats(s):
    z = pd.to_numeric(s, errors="coerce").dropna()
    if z.empty:
        return {
            k: None
            for k in ["count", "mean", "median", "std", "min", "q1", "q3", "max"]
        }
    return {
        "count": int(len(z)),
        "mean": float(z.mean()),
        "median": float(z.median()),
        "std": float(z.std(ddof=1)) if len(z) > 1 else 0.0,
        "min": float(z.min()),
        "q1": float(z.quantile(0.25)),
        "q3": float(z.quantile(0.75)),
        "max": float(z.max()),
    }


def ci95(s):
    z = pd.to_numeric(s, errors="coerce").dropna().to_numpy(float)
    if len(z) == 1:
        return [float(z[0]), float(z[0])]
    m = float(np.mean(z))
    se = float(np.std(z, ddof=1) / math.sqrt(len(z)))
    d = float(t.ppf(0.975, len(z) - 1) * se)
    return [m - d, m + d]


def acceptance(df, attempted):
    completed = len(df)
    improve = float(np.mean(df.calibrated_coverage > df.raw_coverage))
    mc = float(df.calibrated_coverage.mean())
    gap = abs(mc - TARGET)
    reliable = float(
        np.mean(
            (df.calibrated_coverage >= 0.80)
            & (df.calibrated_coverage <= 1.00)
        )
    )
    minimum = float(df.calibrated_coverage.min())
    valid = bool(
        df.raw_intervals_valid.all()
        and df.calibrated_intervals_valid.all()
    )
    finite = bool(
        np.isfinite(
            df[
                [
                    "mae",
                    "rmse",
                    "raw_coverage",
                    "calibrated_coverage",
                    "raw_mean_width",
                    "calibrated_mean_width",
                    "q_hat",
                ]
            ].to_numpy(float)
        ).all()
    )

    items = [
        ["At least 30 successful runs", completed, ">= 30", completed >= 30],
        ["All intervals valid", valid, True, valid],
        [
            "Calibration improves coverage in at least 90% of runs",
            improve,
            ">= 0.90",
            improve >= 0.90,
        ],
        [
            "Mean calibrated coverage is between 85% and 95%",
            mc,
            "0.85 to 0.95",
            0.85 <= mc <= 0.95,
        ],
        [
            "Mean coverage gap is at most 5 percentage points",
            gap,
            "<= 0.05",
            gap <= 0.05,
        ],
        [
            "At least 80% of runs achieve 80% to 100% coverage",
            reliable,
            ">= 0.80",
            reliable >= 0.80,
        ],
        [
            "No calibrated run is below 70% coverage",
            minimum,
            ">= 0.70",
            minimum >= 0.70,
        ],
        ["Core metrics are finite", finite, True, finite],
    ]

    criteria = [
        {"criterion": a, "value": b, "threshold": c, "passed": d}
        for a, b, c, d in items
    ]
    failed = sum(not x["passed"] for x in criteria)
    critical = (
        mc < 0.85
        or minimum < 0.70
        or not valid
        or not finite
        or completed < max(1, int(0.8 * attempted))
    )
    result = (
        "PASS"
        if failed == 0
        else ("FAIL" if critical else "CONDITIONAL PASS")
    )
    return result, criteria


def figures(df, out):
    paths = []

    plt.figure(figsize=(11, 6))
    plt.plot(df.run, df.raw_coverage * 100, marker="o", label="Raw")
    plt.plot(
        df.run,
        df.calibrated_coverage * 100,
        marker="o",
        label="Calibrated",
    )
    plt.axhline(90, ls="--", label="90% target")
    plt.xlabel("Run")
    plt.ylabel("Coverage (%)")
    plt.title("SUANR_V2 Test 03 — Coverage by run")
    plt.legend()
    plt.tight_layout()
    p = out / "SUANR_V2_Test_03_Coverage_By_Run.png"
    plt.savefig(p, dpi=180)
    plt.close()
    paths.append(p)

    plt.figure(figsize=(11, 6))
    plt.plot(df.run, df.mae, marker="o", label="MAE")
    plt.plot(df.run, df.rmse, marker="o", label="RMSE")
    plt.xlabel("Run")
    plt.ylabel("Error")
    plt.title("SUANR_V2 Test 03 — Accuracy by run")
    plt.legend()
    plt.tight_layout()
    p = out / "SUANR_V2_Test_03_Accuracy_By_Run.png"
    plt.savefig(p, dpi=180)
    plt.close()
    paths.append(p)

    plt.figure(figsize=(9, 6))
    plt.hist(df.q_hat, bins=min(12, max(5, len(df) // 2)))
    plt.xlabel("q_hat")
    plt.ylabel("Frequency")
    plt.title("SUANR_V2 Test 03 — q_hat distribution")
    plt.tight_layout()
    p = out / "SUANR_V2_Test_03_QHat_Distribution.png"
    plt.savefig(p, dpi=180)
    plt.close()
    paths.append(p)

    plt.figure(figsize=(9, 6))
    plt.scatter(
        df.calibrated_mean_width,
        df.calibrated_coverage * 100,
    )
    plt.axhline(90, ls="--")
    plt.xlabel("Calibrated mean width")
    plt.ylabel("Coverage (%)")
    plt.title("SUANR_V2 Test 03 — Coverage versus width")
    plt.tight_layout()
    p = out / "SUANR_V2_Test_03_Coverage_Width.png"
    plt.savefig(p, dpi=180)
    plt.close()
    paths.append(p)

    return paths


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "SUANR_V2 Validation Test 03 — repeated-split "
            "calibration stability."
        )
    )
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--ensemble-members", type=int, default=8)
    parser.add_argument("--base-seed", type=int, default=20260727)
    parser.add_argument("--max-iter", type=int, default=1200)
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--auto-download", action="store_true")
    return parser


def parse(argv=None):
    """Parse user options safely in Colab, Jupyter, and normal Python.

    Colab/Jupyter injects arguments such as:
        -f /root/.local/share/jupyter/runtime/kernel-....json

    parse_known_args preserves every supported SUANR option while ignoring
    only arguments that belong to the notebook kernel.
    """
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)

    if unknown:
        notebook_arguments = []
        unexpected_arguments = []
        skip_next = False

        for index, value in enumerate(unknown):
            if skip_next:
                skip_next = False
                continue

            if value in {"-f", "--f"}:
                notebook_arguments.append(value)
                if index + 1 < len(unknown):
                    notebook_arguments.append(unknown[index + 1])
                    skip_next = True
            elif "jupyter/runtime/kernel-" in value or "ipykernel" in value:
                notebook_arguments.append(value)
            else:
                unexpected_arguments.append(value)

        if unexpected_arguments:
            parser.error(
                "unrecognized arguments: "
                + " ".join(unexpected_arguments)
            )

    if args.runs < 1:
        parser.error("--runs must be at least 1.")
    if args.ensemble_members < 3:
        parser.error("--ensemble-members must be at least 3.")
    if args.max_iter < 100:
        parser.error("--max-iter must be at least 100.")

    return Config(
        runs=args.runs,
        ensemble_members=args.ensemble_members,
        base_seed=args.base_seed,
        max_iter=args.max_iter,
        output_dir=args.output_dir,
        auto_download=args.auto_download,
    )


def main(argv=None):
    c = parse(argv)
    out = Path(c.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    warnings.filterwarnings("ignore", category=ConvergenceWarning)

    data = load_diabetes()
    x = np.asarray(data.data, float)
    y = np.asarray(data.target, float)

    print(
        "=" * 79,
        "\nSUANR_V2 Validation Test 03",
        "\nRepeated-Split Calibration Stability and Reliability Test",
        "\n" + "=" * 79,
    )
    print("Runtime: Google Colab/Jupyter compatible")
    print(
        f"Configuration: runs={c.runs}, "
        f"ensemble_members={c.ensemble_members}, "
        f"base_seed={c.base_seed}, max_iter={c.max_iter}"
    )

    rows = []
    for i in range(c.runs):
        seed = c.base_seed + i
        print(
            f"Run {i + 1:02d}/{c.runs} seed={seed} ... ",
            end="",
            flush=True,
        )
        try:
            r = one_run(x, y, i + 1, seed, c)
            print(
                f"raw={r['raw_coverage']:.3f} "
                f"cal={r['calibrated_coverage']:.3f} "
                f"MAE={r['mae']:.2f} q={r['q_hat']:.2f}"
            )
        except Exception as exc:
            r = {
                "run": i + 1,
                "seed": seed,
                "run_status": "FAILED",
                "error_message": f"{type(exc).__name__}: {exc}",
            }
            print(r["error_message"])
        rows.append(r)

    all_df = pd.DataFrame(rows)
    csv_path = out / "SUANR_V2_Test_03_Run_Results.csv"
    all_df.to_csv(csv_path, index=False)

    df = all_df[all_df.run_status == "SUCCESS"].copy()
    if df.empty:
        print("No successful runs. FAIL")
        return 1

    result, criteria = acceptance(df, c.runs)

    cols = [
        "mae",
        "rmse",
        "raw_coverage",
        "calibrated_coverage",
        "raw_coverage_gap",
        "calibrated_coverage_gap",
        "raw_mean_width",
        "calibrated_mean_width",
        "coverage_improvement",
        "width_ratio",
        "q_hat",
        "error_uncertainty_correlation",
        "error_entropy_correlation",
    ]
    aggregate = {key: stats(df[key]) for key in cols}

    if result == "PASS":
        interpretation = (
            "All mandatory criteria were satisfied; repeated "
            "split-conformal calibration was stable."
        )
    elif result == "CONDITIONAL PASS":
        interpretation = (
            "Useful calibration was observed, but one or more "
            "non-critical thresholds were missed."
        )
    else:
        interpretation = (
            "The declared stability criteria were not satisfied; "
            "failed criteria require review."
        )

    summary = {
        "test_name": "SUANR_V2 Validation Test 03",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "researcher": "Martin Pitre",
        "execution_environment": "Google Colab/Jupyter compatible",
        "dataset": {
            "name": "scikit-learn Diabetes",
            "samples": len(x),
            "features": x.shape[1],
        },
        "configuration": asdict(c),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "attempted_runs": c.runs,
        "successful_runs": len(df),
        "failed_runs": c.runs - len(df),
        "seeds": [int(v) for v in df.seed],
        "aggregate_metrics": aggregate,
        "calibrated_coverage_95_ci": ci95(df.calibrated_coverage),
        "calibration_improvement_rate": float(
            np.mean(df.calibrated_coverage > df.raw_coverage)
        ),
        "runs_with_calibrated_coverage_80_to_100_rate": float(
            np.mean(
                (df.calibrated_coverage >= 0.8)
                & (df.calibrated_coverage <= 1.0)
            )
        ),
        "acceptance_criteria": criteria,
        "overall_result": result,
        "interpretation": interpretation,
        "scientific_note": (
            "This test evaluates repeated-split stability on one "
            "dataset, not cross-dataset generalization."
        ),
    }

    json_path = out / "SUANR_V2_Test_03_Summary.json"
    json_path.write_text(
        json.dumps(summary, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    summary_path = out / "SUANR_V2_Test_03_Summary.txt"
    lines = [
        "=" * 79,
        "SUANR_V2 VALIDATION TEST 03 — FINAL SUMMARY",
        "=" * 79,
        f"Overall result: {result}",
        f"Successful runs: {len(df)}/{c.runs}",
        f"Mean raw coverage: {aggregate['raw_coverage']['mean']:.4f}",
        (
            "Mean calibrated coverage: "
            f"{aggregate['calibrated_coverage']['mean']:.4f}"
        ),
        f"95% CI: {summary['calibrated_coverage_95_ci']}",
        f"Mean MAE: {aggregate['mae']['mean']:.4f}",
        f"Mean RMSE: {aggregate['rmse']['mean']:.4f}",
        "",
        "ACCEPTANCE CRITERIA",
    ]
    lines.extend(
        (
            f"[{'PASS' if item['passed'] else 'FAIL'}] "
            f"{item['criterion']} | value={item['value']} | "
            f"threshold={item['threshold']}"
        )
        for item in criteria
    )
    lines.extend(["", interpretation])
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    figure_paths = figures(df, out)
    package_path = out / "SUANR_V2_Test_03_Evidence_Package.zip"

    with zipfile.ZipFile(
        package_path,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        for artifact in [
            csv_path,
            json_path,
            summary_path,
            *figure_paths,
        ]:
            archive.write(artifact, artifact.name)

    print(summary_path.read_text(encoding="utf-8"))
    print("\nGenerated:")
    for artifact in [
        csv_path,
        json_path,
        summary_path,
        *figure_paths,
        package_path,
    ]:
        print(artifact)

    if c.auto_download:
        try:
            from google.colab import files
            files.download(str(package_path))
        except ImportError:
            print(
                "--auto-download was requested, but this runtime is "
                "not Google Colab."
            )

    return 0 if result in {"PASS", "CONDITIONAL PASS"} else 2


if __name__ == "__main__":
    # Do not call sys.exit() inside an active notebook kernel. IPython displays
    # SystemExit as an exception even when the return code is zero.
    exit_code = main()
    running_in_notebook = "ipykernel" in sys.modules

    if not running_in_notebook:
        raise SystemExit(exit_code)
    elif exit_code != 0:
        print(f"\nTest completed with status code {exit_code}.")
