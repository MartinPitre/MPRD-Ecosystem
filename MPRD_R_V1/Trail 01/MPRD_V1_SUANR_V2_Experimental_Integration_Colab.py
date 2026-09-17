# ============================================================
# MPRD_V1 + SUANR_V2 EXPERIMENTAL INTEGRATION PROTOTYPE
# Google Colab: copy this entire script into one cell and run.
#
# IMPORTANT RESEARCH BOUNDARY
# ------------------------------------------------------------
# - MPRD_V1 remains the frozen standalone baseline.
# - SUANR_V2 is connected through an external adapter.
# - This prototype does NOT overwrite or redefine MPRD_V1.
# - It compares:
#       A) Baseline recursive reasoning
#       B) Uncertainty-aware recursive reasoning
#
# The uncertainty adapter can later be replaced by the exact
# validated SUANR_V2 model and calibration pipeline.
# ============================================================

import json
import math
import hashlib
import statistics
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Tuple, Optional
from copy import deepcopy
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

try:
    from sklearn.datasets import make_regression
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error
except ImportError as exc:
    raise RuntimeError(
        "This script requires scikit-learn, which is normally available in Google Colab."
    ) from exc


# ============================================================
# 1. REPRODUCIBILITY SETTINGS
# ============================================================

GLOBAL_SEED = 47
np.random.seed(GLOBAL_SEED)

OUTPUT_DIR = Path("MPRD_SUANR_V2_Integration_Output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# 2. DATA STRUCTURES
# ============================================================

@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    group_id: str
    direction: str              # "SUPPORT" or "CONTRADICT"
    strength: float             # [0, 1]
    reliability: float          # [0, 1]
    feature_vector: Tuple[float, ...]
    observed_target: float
    description: str = ""


@dataclass
class UncertaintyAssessment:
    evidence_id: str
    prediction: float
    lower: float
    upper: float
    interval_width: float
    normalized_uncertainty: float
    certainty_factor: float
    calibration_residual: float


@dataclass
class ClaimState:
    cycle: int = 0
    status: str = "CANDIDATE"
    raw_support: float = 0.0
    raw_contradiction: float = 0.0
    adjusted_support: float = 0.0
    adjusted_contradiction: float = 0.0
    confidence: float = 0.0
    persistence: float = 0.0
    independent_groups: int = 0
    evidence_count: int = 0
    stable_cycles: int = 0
    state_digest: str = ""


@dataclass
class AuditRecord:
    cycle: int
    evidence_id: str
    event: str
    baseline_weight: float
    uncertainty: float
    certainty_factor: float
    effective_weight: float
    status_after: str
    confidence_after: float
    persistence_after: float
    state_digest: str


# ============================================================
# 3. SUANR_V2-LIKE UNCERTAINTY ADAPTER
# ============================================================

class SUANRAdapter:
    """
    Experimental adapter that approximates the validated SUANR_V2 role:
    - ensemble prediction
    - dispersion-based uncertainty
    - residual calibration
    - predictive interval
    - normalized uncertainty in [0, 1]

    Replace this class later with the exact validated SUANR_V2 pipeline.
    """

    def __init__(
        self,
        n_members: int = 6,
        nominal_coverage: float = 0.90,
        random_seed: int = GLOBAL_SEED,
    ):
        self.n_members = n_members
        self.nominal_coverage = nominal_coverage
        self.random_seed = random_seed
        self.models: List[RandomForestRegressor] = []
        self.calibration_quantile: Optional[float] = None
        self.width_scale: Optional[float] = None
        self.is_fitted = False

    def fit(self, X_train, y_train, X_cal, y_cal):
        self.models = []

        for member in range(self.n_members):
            seed = self.random_seed + member * 101
            model = RandomForestRegressor(
                n_estimators=120,
                max_depth=6,
                min_samples_leaf=3,
                bootstrap=True,
                random_state=seed,
                n_jobs=-1,
            )
            model.fit(X_train, y_train)
            self.models.append(model)

        cal_matrix = np.column_stack(
            [model.predict(X_cal) for model in self.models]
        )
        cal_mean = cal_matrix.mean(axis=1)
        cal_std = cal_matrix.std(axis=1, ddof=1)

        # Conformal-style residual calibration around ensemble uncertainty.
        # The floor prevents division by zero.
        standardized_residuals = np.abs(y_cal - cal_mean) / np.maximum(cal_std, 1e-8)
        self.calibration_quantile = float(
            np.quantile(standardized_residuals, self.nominal_coverage)
        )

        raw_widths = 2.0 * self.calibration_quantile * np.maximum(cal_std, 1e-8)
        self.width_scale = float(np.quantile(raw_widths, 0.95))
        if self.width_scale <= 0:
            self.width_scale = 1.0

        self.is_fitted = True
        return self

    def assess(
        self,
        evidence_id: str,
        feature_vector: Tuple[float, ...],
        observed_target: float,
    ) -> UncertaintyAssessment:
        if not self.is_fitted:
            raise RuntimeError("SUANRAdapter must be fitted before assess().")

        x = np.asarray(feature_vector, dtype=float).reshape(1, -1)
        predictions = np.array([model.predict(x)[0] for model in self.models])

        pred_mean = float(predictions.mean())
        pred_std = float(predictions.std(ddof=1))

        half_width = self.calibration_quantile * max(pred_std, 1e-8)
        lower = pred_mean - half_width
        upper = pred_mean + half_width
        width = upper - lower

        normalized_uncertainty = float(np.clip(width / self.width_scale, 0.0, 1.0))
        certainty_factor = 1.0 - normalized_uncertainty
        calibration_residual = abs(observed_target - pred_mean)

        return UncertaintyAssessment(
            evidence_id=evidence_id,
            prediction=pred_mean,
            lower=float(lower),
            upper=float(upper),
            interval_width=float(width),
            normalized_uncertainty=normalized_uncertainty,
            certainty_factor=certainty_factor,
            calibration_residual=float(calibration_residual),
        )


# ============================================================
# 4. FROZEN-BASELINE MPRD REASONING ENGINE
# ============================================================

class MPRDRecursiveEngine:
    """
    Experimental reconstruction of the validated MPRD recursive process.

    Baseline mode:
        effective_weight = strength * reliability

    Integrated mode:
        effective_weight = strength * reliability * uncertainty_gate

    The uncertainty gate is external to the frozen baseline:
        uncertainty_gate = floor + (1 - floor) * certainty_factor

    This avoids allowing uncertain evidence to become zero-weight unless
    explicitly designed that way.
    """

    VALID_DIRECTIONS = {"SUPPORT", "CONTRADICT"}

    def __init__(
        self,
        mode: str,
        uncertainty_floor: float = 0.25,
        stability_tolerance: float = 1e-10,
        required_stable_cycles: int = 2,
    ):
        if mode not in {"BASELINE", "SUANR_AWARE"}:
            raise ValueError("mode must be BASELINE or SUANR_AWARE")

        self.mode = mode
        self.uncertainty_floor = uncertainty_floor
        self.stability_tolerance = stability_tolerance
        self.required_stable_cycles = required_stable_cycles

        self.state = ClaimState()
        self.accepted_evidence: Dict[str, Evidence] = {}
        self.uncertainty_map: Dict[str, UncertaintyAssessment] = {}
        self.audit_log: List[AuditRecord] = []
        self.previous_numeric_state: Optional[Tuple[float, ...]] = None

    @staticmethod
    def _bounded(value: float) -> float:
        return float(np.clip(value, 0.0, 1.0))

    def _classify(self, confidence: float, contradiction: float, persistence: float) -> str:
        if self.state.evidence_count == 0:
            return "CANDIDATE"
        if confidence >= 0.65 and contradiction < 0.30 and persistence >= 0.70:
            return "PERSISTENT"
        if confidence >= 0.55 and contradiction < 0.40:
            return "SUPPORTED"
        if contradiction >= 0.30 and confidence >= 0.40:
            return "CONTESTED"
        if contradiction >= 0.65 and confidence < 0.40:
            return "REJECTED"
        return "CANDIDATE"

    def _digest_state(self) -> str:
        payload = {
            "mode": self.mode,
            "cycle": self.state.cycle,
            "status": self.state.status,
            "raw_support": round(self.state.raw_support, 12),
            "raw_contradiction": round(self.state.raw_contradiction, 12),
            "adjusted_support": round(self.state.adjusted_support, 12),
            "adjusted_contradiction": round(self.state.adjusted_contradiction, 12),
            "confidence": round(self.state.confidence, 12),
            "persistence": round(self.state.persistence, 12),
            "groups": self.state.independent_groups,
            "evidence_count": self.state.evidence_count,
            "evidence_ids": sorted(self.accepted_evidence),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _effective_weight(
        self,
        evidence: Evidence,
        uncertainty: Optional[UncertaintyAssessment],
    ) -> Tuple[float, float, float]:
        baseline_weight = evidence.strength * evidence.reliability

        if self.mode == "BASELINE":
            return baseline_weight, 0.0, baseline_weight

        if uncertainty is None:
            raise ValueError("SUANR_AWARE mode requires an uncertainty assessment.")

        gate = self.uncertainty_floor + (
            1.0 - self.uncertainty_floor
        ) * uncertainty.certainty_factor

        effective_weight = baseline_weight * gate
        return baseline_weight, gate, effective_weight

    def add_evidence(
        self,
        evidence: Evidence,
        uncertainty: Optional[UncertaintyAssessment] = None,
    ):
        if evidence.evidence_id in self.accepted_evidence:
            raise ValueError(f"Duplicate evidence rejected: {evidence.evidence_id}")
        if evidence.direction not in self.VALID_DIRECTIONS:
            raise ValueError(f"Invalid direction: {evidence.direction}")
        if not (0.0 <= evidence.strength <= 1.0):
            raise ValueError("strength must be within [0, 1]")
        if not (0.0 <= evidence.reliability <= 1.0):
            raise ValueError("reliability must be within [0, 1]")

        self.accepted_evidence[evidence.evidence_id] = evidence
        if uncertainty is not None:
            self.uncertainty_map[evidence.evidence_id] = uncertainty

        self.state.cycle += 1
        self._recompute_state()

        baseline_weight, gate, effective_weight = self._effective_weight(
            evidence, uncertainty
        )

        u = uncertainty.normalized_uncertainty if uncertainty else 0.0
        c = uncertainty.certainty_factor if uncertainty else 1.0

        self.audit_log.append(
            AuditRecord(
                cycle=self.state.cycle,
                evidence_id=evidence.evidence_id,
                event="EVIDENCE_ACCEPTED",
                baseline_weight=baseline_weight,
                uncertainty=u,
                certainty_factor=c,
                effective_weight=effective_weight,
                status_after=self.state.status,
                confidence_after=self.state.confidence,
                persistence_after=self.state.persistence,
                state_digest=self.state.state_digest,
            )
        )

    def _recompute_state(self):
        support_raw = 0.0
        contradiction_raw = 0.0
        support_effective = 0.0
        contradiction_effective = 0.0

        groups = set()

        for evidence_id in sorted(self.accepted_evidence):
            evidence = self.accepted_evidence[evidence_id]
            uncertainty = self.uncertainty_map.get(evidence_id)
            baseline_weight, _, effective_weight = self._effective_weight(
                evidence, uncertainty
            )

            groups.add(evidence.group_id)

            if evidence.direction == "SUPPORT":
                # Saturating aggregation preserves bounded scores.
                support_raw = 1.0 - (1.0 - support_raw) * (1.0 - baseline_weight)
                support_effective = 1.0 - (
                    (1.0 - support_effective) * (1.0 - effective_weight)
                )
            else:
                contradiction_raw = 1.0 - (
                    (1.0 - contradiction_raw) * (1.0 - baseline_weight)
                )
                contradiction_effective = 1.0 - (
                    (1.0 - contradiction_effective) * (1.0 - effective_weight)
                )

        evidence_count = len(self.accepted_evidence)
        independent_groups = len(groups)

        # Conservative confidence:
        # support is reduced by contradiction, while independent groups add
        # a modest corroboration factor.
        independence_factor = 1.0 - math.exp(-0.45 * independent_groups)
        confidence = support_effective * (1.0 - 0.55 * contradiction_effective)
        confidence *= 0.70 + 0.30 * independence_factor
        confidence = self._bounded(confidence)

        # Persistence increases with repeated independent evidence, but is
        # weakened by contradiction.
        accumulation = 1.0 - math.exp(-0.70 * evidence_count)
        persistence = (
            0.60 * accumulation
            + 0.40 * confidence
        ) * (1.0 - 0.25 * contradiction_effective)
        persistence = self._bounded(persistence)

        numeric_state = (
            support_effective,
            contradiction_effective,
            confidence,
            persistence,
        )

        if self.previous_numeric_state is not None:
            delta = max(
                abs(a - b)
                for a, b in zip(numeric_state, self.previous_numeric_state)
            )
            if delta <= self.stability_tolerance:
                self.state.stable_cycles += 1
            else:
                self.state.stable_cycles = 0

        self.previous_numeric_state = numeric_state

        self.state.raw_support = self._bounded(support_raw)
        self.state.raw_contradiction = self._bounded(contradiction_raw)
        self.state.adjusted_support = self._bounded(support_effective)
        self.state.adjusted_contradiction = self._bounded(contradiction_effective)
        self.state.confidence = confidence
        self.state.persistence = persistence
        self.state.independent_groups = independent_groups
        self.state.evidence_count = evidence_count
        self.state.status = self._classify(
            confidence=confidence,
            contradiction=contradiction_effective,
            persistence=persistence,
        )
        self.state.state_digest = self._digest_state()

    def run_stability_cycles(self, max_cycles: int = 10):
        """
        Recompute without new evidence to verify stable convergence.
        """
        for _ in range(max_cycles):
            if self.state.stable_cycles >= self.required_stable_cycles:
                break
            self.state.cycle += 1
            self._recompute_state()

            self.audit_log.append(
                AuditRecord(
                    cycle=self.state.cycle,
                    evidence_id="NONE",
                    event="STABILITY_RECOMPUTE",
                    baseline_weight=0.0,
                    uncertainty=0.0,
                    certainty_factor=1.0,
                    effective_weight=0.0,
                    status_after=self.state.status,
                    confidence_after=self.state.confidence,
                    persistence_after=self.state.persistence,
                    state_digest=self.state.state_digest,
                )
            )


# ============================================================
# 5. SYNTHETIC SUANR TRAINING DATA
# ============================================================

def build_suanr_training_data():
    X, y = make_regression(
        n_samples=900,
        n_features=6,
        n_informative=6,
        noise=18.0,
        random_state=GLOBAL_SEED,
    )

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.40, random_state=GLOBAL_SEED
    )
    X_cal, X_test, y_cal, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=GLOBAL_SEED
    )

    adapter = SUANRAdapter(
        n_members=6,
        nominal_coverage=0.90,
        random_seed=GLOBAL_SEED,
    )
    adapter.fit(X_train, y_train, X_cal, y_cal)

    test_matrix = np.column_stack(
        [model.predict(X_test) for model in adapter.models]
    )
    test_mean = test_matrix.mean(axis=1)
    test_std = test_matrix.std(axis=1, ddof=1)
    half_width = adapter.calibration_quantile * np.maximum(test_std, 1e-8)
    lower = test_mean - half_width
    upper = test_mean + half_width

    coverage = float(np.mean((y_test >= lower) & (y_test <= upper)))
    mae = float(mean_absolute_error(y_test, test_mean))
    mean_width = float(np.mean(upper - lower))

    diagnostics = {
        "nominal_coverage": adapter.nominal_coverage,
        "empirical_test_coverage": coverage,
        "test_mae": mae,
        "mean_interval_width": mean_width,
        "calibration_quantile": adapter.calibration_quantile,
        "n_members": adapter.n_members,
    }

    return adapter, X_test, y_test, diagnostics


# ============================================================
# 6. EXPERIMENTAL EVIDENCE PACKET
# ============================================================

def build_evidence_packet(X_test, y_test) -> List[Evidence]:
    """
    Selects evidence with varied uncertainty and both support/contradiction.
    The evidence direction remains an MPRD input; SUANR only estimates
    predictive uncertainty for that evidence context.
    """
    indices = [3, 17, 42, 88, 121, 150]

    directions = [
        "SUPPORT",
        "SUPPORT",
        "CONTRADICT",
        "SUPPORT",
        "CONTRADICT",
        "SUPPORT",
    ]

    strengths = [0.88, 0.76, 0.66, 0.91, 0.58, 0.81]
    reliabilities = [0.92, 0.83, 0.78, 0.95, 0.72, 0.87]

    packet = []
    for i, idx in enumerate(indices, start=1):
        packet.append(
            Evidence(
                evidence_id=f"E{i:02d}",
                group_id=f"G{i:02d}",
                direction=directions[i - 1],
                strength=strengths[i - 1],
                reliability=reliabilities[i - 1],
                feature_vector=tuple(float(v) for v in X_test[idx]),
                observed_target=float(y_test[idx]),
                description=f"Synthetic integration evidence {i}",
            )
        )
    return packet


# ============================================================
# 7. RUN BASELINE AND INTEGRATED CONFIGURATIONS
# ============================================================

def run_configuration(
    mode: str,
    evidence_packet: List[Evidence],
    adapter: SUANRAdapter,
):
    engine = MPRDRecursiveEngine(mode=mode)

    cycle_history = []

    for evidence in evidence_packet:
        uncertainty = None
        if mode == "SUANR_AWARE":
            uncertainty = adapter.assess(
                evidence_id=evidence.evidence_id,
                feature_vector=evidence.feature_vector,
                observed_target=evidence.observed_target,
            )

        engine.add_evidence(evidence, uncertainty)

        cycle_history.append({
            "cycle": engine.state.cycle,
            "evidence_id": evidence.evidence_id,
            "direction": evidence.direction,
            "status": engine.state.status,
            "raw_support": engine.state.raw_support,
            "raw_contradiction": engine.state.raw_contradiction,
            "adjusted_support": engine.state.adjusted_support,
            "adjusted_contradiction": engine.state.adjusted_contradiction,
            "confidence": engine.state.confidence,
            "persistence": engine.state.persistence,
            "state_digest": engine.state.state_digest,
        })

    engine.run_stability_cycles()

    return engine, cycle_history


# ============================================================
# 8. DETERMINISM CHECK
# ============================================================

def normalized_run_digest(engine: MPRDRecursiveEngine) -> str:
    payload = {
        "mode": engine.mode,
        "state": {
            "status": engine.state.status,
            "raw_support": round(engine.state.raw_support, 12),
            "raw_contradiction": round(engine.state.raw_contradiction, 12),
            "adjusted_support": round(engine.state.adjusted_support, 12),
            "adjusted_contradiction": round(engine.state.adjusted_contradiction, 12),
            "confidence": round(engine.state.confidence, 12),
            "persistence": round(engine.state.persistence, 12),
            "independent_groups": engine.state.independent_groups,
            "evidence_count": engine.state.evidence_count,
        },
        "audit": [
            {
                "cycle": r.cycle,
                "evidence_id": r.evidence_id,
                "event": r.event,
                "baseline_weight": round(r.baseline_weight, 12),
                "uncertainty": round(r.uncertainty, 12),
                "certainty_factor": round(r.certainty_factor, 12),
                "effective_weight": round(r.effective_weight, 12),
                "status_after": r.status_after,
                "confidence_after": round(r.confidence_after, 12),
                "persistence_after": round(r.persistence_after, 12),
            }
            for r in engine.audit_log
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def repeatability_test(adapter, evidence_packet, runs=30):
    baseline_digests = []
    integrated_digests = []

    for _ in range(runs):
        baseline_engine, _ = run_configuration(
            "BASELINE", evidence_packet, adapter
        )
        integrated_engine, _ = run_configuration(
            "SUANR_AWARE", evidence_packet, adapter
        )

        baseline_digests.append(normalized_run_digest(baseline_engine))
        integrated_digests.append(normalized_run_digest(integrated_engine))

    return {
        "runs": runs,
        "baseline_unique_digests": len(set(baseline_digests)),
        "integrated_unique_digests": len(set(integrated_digests)),
        "baseline_deterministic": len(set(baseline_digests)) == 1,
        "integrated_deterministic": len(set(integrated_digests)) == 1,
        "baseline_digest": baseline_digests[0],
        "integrated_digest": integrated_digests[0],
    }


# ============================================================
# 9. OUTPUTS AND FIGURES
# ============================================================

def save_json(filename: str, payload):
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def create_figures(
    baseline_history,
    integrated_history,
    integrated_engine,
):
    cycles = [row["cycle"] for row in baseline_history]

    # Figure 1: Confidence
    plt.figure(figsize=(9, 5))
    plt.plot(cycles, [r["confidence"] for r in baseline_history], marker="o", label="MPRD baseline")
    plt.plot(cycles, [r["confidence"] for r in integrated_history], marker="o", label="MPRD + SUANR")
    plt.xlabel("Recursive evidence cycle")
    plt.ylabel("Confidence")
    plt.title("Confidence Across Recursive Cycles")
    plt.ylim(0, 1)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "Figure_01_Confidence_Comparison.png", dpi=180)
    plt.show()

    # Figure 2: Persistence
    plt.figure(figsize=(9, 5))
    plt.plot(cycles, [r["persistence"] for r in baseline_history], marker="o", label="MPRD baseline")
    plt.plot(cycles, [r["persistence"] for r in integrated_history], marker="o", label="MPRD + SUANR")
    plt.xlabel("Recursive evidence cycle")
    plt.ylabel("Persistence")
    plt.title("Persistence Across Recursive Cycles")
    plt.ylim(0, 1)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "Figure_02_Persistence_Comparison.png", dpi=180)
    plt.show()

    # Figure 3: Uncertainty by evidence
    accepted_records = [
        record for record in integrated_engine.audit_log
        if record.event == "EVIDENCE_ACCEPTED"
    ]
    ids = [r.evidence_id for r in accepted_records]
    uncertainties = [r.uncertainty for r in accepted_records]
    effective_weights = [r.effective_weight for r in accepted_records]

    x = np.arange(len(ids))
    width = 0.36

    plt.figure(figsize=(9, 5))
    plt.bar(x - width / 2, uncertainties, width, label="Normalized uncertainty")
    plt.bar(x + width / 2, effective_weights, width, label="Effective evidence weight")
    plt.xticks(x, ids)
    plt.xlabel("Evidence item")
    plt.ylabel("Score")
    plt.title("SUANR Uncertainty and MPRD Effective Weight")
    plt.ylim(0, 1)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "Figure_03_Uncertainty_and_Weight.png", dpi=180)
    plt.show()


# ============================================================
# 10. MAIN EXECUTION
# ============================================================

def main():
    print("=" * 100)
    print("MPRD_V1 + SUANR_V2 Experimental Recursive Loop Integration")
    print("=" * 100)

    adapter, X_test, y_test, suanr_diagnostics = build_suanr_training_data()
    evidence_packet = build_evidence_packet(X_test, y_test)

    baseline_engine, baseline_history = run_configuration(
        "BASELINE", evidence_packet, adapter
    )
    integrated_engine, integrated_history = run_configuration(
        "SUANR_AWARE", evidence_packet, adapter
    )

    repeatability = repeatability_test(
        adapter=adapter,
        evidence_packet=evidence_packet,
        runs=30,
    )

    baseline_state = asdict(baseline_engine.state)
    integrated_state = asdict(integrated_engine.state)

    comparison = {
        "confidence_change": (
            integrated_engine.state.confidence
            - baseline_engine.state.confidence
        ),
        "persistence_change": (
            integrated_engine.state.persistence
            - baseline_engine.state.persistence
        ),
        "adjusted_support_change": (
            integrated_engine.state.adjusted_support
            - baseline_engine.state.adjusted_support
        ),
        "adjusted_contradiction_change": (
            integrated_engine.state.adjusted_contradiction
            - baseline_engine.state.adjusted_contradiction
        ),
        "baseline_status": baseline_engine.state.status,
        "integrated_status": integrated_engine.state.status,
    }

    results = {
        "research_boundary": {
            "mprd_v1_status": "FROZEN_BASELINE_PRESERVED",
            "integration_status": "EXPERIMENTAL_EXTERNAL_ADAPTER",
            "claim": (
                "This prototype demonstrates an integration method; "
                "it does not validate the final architecture."
            ),
        },
        "suanr_diagnostics": suanr_diagnostics,
        "baseline_final_state": baseline_state,
        "integrated_final_state": integrated_state,
        "comparison": comparison,
        "repeatability": repeatability,
        "evidence_packet": [asdict(e) for e in evidence_packet],
        "uncertainty_assessments": {
            key: asdict(value)
            for key, value in integrated_engine.uncertainty_map.items()
        },
        "baseline_history": baseline_history,
        "integrated_history": integrated_history,
        "baseline_audit": [asdict(r) for r in baseline_engine.audit_log],
        "integrated_audit": [asdict(r) for r in integrated_engine.audit_log],
    }

    save_json("MPRD_SUANR_V2_Integration_Results.json", results)
    save_json("MPRD_Baseline_Audit.json", results["baseline_audit"])
    save_json("MPRD_SUANR_Integrated_Audit.json", results["integrated_audit"])

    create_figures(
        baseline_history=baseline_history,
        integrated_history=integrated_history,
        integrated_engine=integrated_engine,
    )

    summary_lines = [
        "=" * 100,
        "MPRD_V1 + SUANR_V2 EXPERIMENTAL INTEGRATION SUMMARY",
        "=" * 100,
        f"SUANR nominal coverage:          {suanr_diagnostics['nominal_coverage']:.3f}",
        f"SUANR empirical test coverage:  {suanr_diagnostics['empirical_test_coverage']:.3f}",
        f"SUANR test MAE:                 {suanr_diagnostics['test_mae']:.6f}",
        "-" * 100,
        f"Baseline final status:          {baseline_engine.state.status}",
        f"Integrated final status:        {integrated_engine.state.status}",
        f"Baseline confidence:            {baseline_engine.state.confidence:.8f}",
        f"Integrated confidence:          {integrated_engine.state.confidence:.8f}",
        f"Confidence change:              {comparison['confidence_change']:+.8f}",
        f"Baseline persistence:           {baseline_engine.state.persistence:.8f}",
        f"Integrated persistence:         {integrated_engine.state.persistence:.8f}",
        f"Persistence change:             {comparison['persistence_change']:+.8f}",
        "-" * 100,
        f"Repeatability runs:             {repeatability['runs']}",
        f"Baseline deterministic:         {repeatability['baseline_deterministic']}",
        f"Integrated deterministic:       {repeatability['integrated_deterministic']}",
        f"Baseline unique digests:        {repeatability['baseline_unique_digests']}",
        f"Integrated unique digests:      {repeatability['integrated_unique_digests']}",
        "-" * 100,
        "INTERPRETATION:",
        "The script compares the frozen MPRD-style baseline with an external",
        "SUANR uncertainty adapter. Uncertain evidence is discounted rather than",
        "discarded, and every adjustment is preserved in the audit log.",
        "",
        "This is an integration experiment, not a completed validation claim.",
        "=" * 100,
    ]

    summary_text = "\n".join(summary_lines)
    print(summary_text)

    (OUTPUT_DIR / "MPRD_SUANR_V2_Integration_Summary.txt").write_text(
        summary_text, encoding="utf-8"
    )

    # Zip all outputs.
    import shutil
    zip_path = shutil.make_archive(
        "MPRD_SUANR_V2_Integration_Output",
        "zip",
        OUTPUT_DIR,
    )
    print(f"\nOutput package created: {zip_path}")

    # Automatic downloads in Colab.
    try:
        from google.colab import files
        files.download(zip_path)
    except Exception:
        print("Automatic download skipped because this is not running in Google Colab.")


if __name__ == "__main__":
    main()
