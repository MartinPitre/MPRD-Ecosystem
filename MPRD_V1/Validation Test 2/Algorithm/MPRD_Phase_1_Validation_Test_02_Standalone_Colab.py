# ======================================================================================
# MPRD Phase 1 Validation Test 02
# Recursive Evidence Integration and Knowledge Evolution
#
# Standalone Google Colab script
# Copy and paste this entire file into one Colab cell, then run it.
#
# Purpose:
#   Validate deterministic recursive claim-state revision across supporting and
#   conflicting evidence cycles while preserving a complete audit history.
#
# Scientific outcome and execution completeness are reported separately.
# ======================================================================================

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import shutil
import sys
import time
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Tuple

# Matplotlib is preinstalled in Google Colab.
import matplotlib.pyplot as plt


# ======================================================================================
# 1. FIXED TEST CONFIGURATION
# ======================================================================================

TEST_NAME = "MPRD Phase 1 Validation Test 02"
TEST_SUBTITLE = "Recursive Evidence Integration and Knowledge Evolution"
ALGORITHM_VERSION = "MPRD_V1 Core Algorithm v1.0 — Validation Harness 02"
SCHEMA_VERSION = "1.0"

REPEATABILITY_RUNS = 30

OUTPUT_DIR = Path("MPRD_Phase_1_Validation_Test_02_Evidence")
ZIP_BASENAME = "MPRD_Phase_1_Validation_Test_02_Complete_Evidence_Package"

# A single claim is intentionally used so that recursive state evolution remains
# transparent and directly auditable.
CLAIM_ID = "CLM-001"
CLAIM_TEXT = "The test output is reproducible."

# Evidence sequence:
#   Cycle 1 — initial support
#   Cycle 2 — independent reinforcement
#   Cycle 3 — credible conflict
#   Cycle 4 — additional independent support
#
# Reliability is bounded to [0, 1].
# Independence groups prevent repeated evidence from the same group from being
# treated as fully independent reinforcement.
EVIDENCE_SEQUENCE = [
    {
        "cycle": 1,
        "evidence_id": "EV-001",
        "source": "Independent Replication Group A",
        "independence_group": "GROUP-A",
        "stance": "support",
        "reliability": 0.90,
        "description": "A fixed-input execution produced the expected output.",
    },
    {
        "cycle": 2,
        "evidence_id": "EV-002",
        "source": "Independent Replication Group B",
        "independence_group": "GROUP-B",
        "stance": "support",
        "reliability": 0.85,
        "description": "A separate group reproduced the expected output.",
    },
    {
        "cycle": 3,
        "evidence_id": "EV-003",
        "source": "Independent Challenge Group C",
        "independence_group": "GROUP-C",
        "stance": "conflict",
        "reliability": 0.70,
        "description": "A controlled challenge reported a non-matching output.",
    },
    {
        "cycle": 4,
        "evidence_id": "EV-004",
        "source": "Independent Replication Group D",
        "independence_group": "GROUP-D",
        "stance": "support",
        "reliability": 0.95,
        "description": "A fourth group reproduced the expected output under the fixed protocol.",
    },
]

STANCE = Literal["support", "conflict"]


# ======================================================================================
# 2. DATA MODELS
# ======================================================================================

@dataclass(frozen=True)
class Evidence:
    cycle: int
    evidence_id: str
    source: str
    independence_group: str
    stance: STANCE
    reliability: float
    description: str


@dataclass
class ClaimState:
    claim_id: str
    claim_text: str
    cycle: int = 0
    support_score: float = 0.0
    conflict_score: float = 0.0
    confidence: float = 0.5
    persistence: float = 0.0
    status: str = "OPEN"
    accepted_evidence: int = 0
    support_count: int = 0
    conflict_count: int = 0
    independent_groups: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)


# ======================================================================================
# 3. DETERMINISTIC MPRD VALIDATION FUNCTIONS
# ======================================================================================

def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value to a closed interval."""
    return max(low, min(high, value))


def validate_evidence(evidence: Evidence) -> None:
    """Reject malformed evidence before it can affect state."""
    if evidence.cycle < 1:
        raise ValueError("Evidence cycle must be >= 1.")
    if not evidence.evidence_id.strip():
        raise ValueError("Evidence ID cannot be empty.")
    if not evidence.source.strip():
        raise ValueError("Evidence source cannot be empty.")
    if not evidence.independence_group.strip():
        raise ValueError("Independence group cannot be empty.")
    if evidence.stance not in ("support", "conflict"):
        raise ValueError(f"Unsupported stance: {evidence.stance}")
    if not 0.0 <= evidence.reliability <= 1.0:
        raise ValueError("Reliability must be between 0 and 1.")


def independence_weight(group: str, previous_groups: List[str]) -> float:
    """
    New independent groups receive full weight.
    Repeated evidence from an existing group receives reduced weight.
    """
    return 1.0 if group not in previous_groups else 0.35


def calculate_confidence(support_score: float, conflict_score: float) -> float:
    """
    Transparent confidence calculation.

    A neutral prior of 1.0 is added to both sides. Confidence is the supported
    share of total accumulated weighted evidence.

        confidence = (support + 1) / (support + conflict + 2)

    This prevents absolute certainty and allows confidence to rise or fall
    proportionally as evidence accumulates.
    """
    return (support_score + 1.0) / (support_score + conflict_score + 2.0)


def calculate_persistence(
    support_score: float,
    conflict_score: float,
    independent_group_count: int,
    cycle: int,
) -> float:
    """
    Persistence combines:
      - accumulated support,
      - diversity of independent sources,
      - recurrence across cycles,
      - and a penalty for unresolved conflict.

    The logistic transform keeps the result within [0, 1].
    """
    raw = (
        0.90 * support_score
        + 0.25 * independent_group_count
        + 0.12 * cycle
        - 0.85 * conflict_score
        - 1.25
    )
    return 1.0 / (1.0 + math.exp(-raw))


def classify_status(
    confidence: float,
    persistence: float,
    support_count: int,
    conflict_count: int,
) -> str:
    """Assign a deterministic claim state."""
    if confidence >= 0.65 and persistence >= 0.70 and support_count >= 2:
        return "PERSISTENT"
    if conflict_count > 0 and 0.40 <= confidence < 0.65:
        return "CONTESTED"
    if confidence >= 0.60 and support_count >= 1:
        return "SUPPORTED"
    if confidence < 0.40 and conflict_count > support_count:
        return "WEAKENED"
    return "OPEN"


def stable_digest(payload: object) -> str:
    """Create a deterministic SHA-256 digest from JSON-compatible content."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def apply_evidence(
    prior_state: ClaimState,
    evidence: Evidence,
) -> Tuple[ClaimState, Dict[str, object]]:
    """Apply one evidence item and return the revised state plus audit record."""
    validate_evidence(evidence)

    state = deepcopy(prior_state)
    before = asdict(state)

    weight = independence_weight(evidence.independence_group, state.independent_groups)
    weighted_value = evidence.reliability * weight

    if evidence.stance == "support":
        state.support_score += weighted_value
        state.support_count += 1
    else:
        state.conflict_score += weighted_value
        state.conflict_count += 1

    if evidence.independence_group not in state.independent_groups:
        state.independent_groups.append(evidence.independence_group)

    state.evidence_ids.append(evidence.evidence_id)
    state.accepted_evidence += 1
    state.cycle = evidence.cycle

    state.confidence = calculate_confidence(
        state.support_score,
        state.conflict_score,
    )
    state.persistence = calculate_persistence(
        state.support_score,
        state.conflict_score,
        len(state.independent_groups),
        state.cycle,
    )
    state.status = classify_status(
        state.confidence,
        state.persistence,
        state.support_count,
        state.conflict_count,
    )

    # Round only after all calculations to keep reporting stable.
    state.support_score = round(state.support_score, 8)
    state.conflict_score = round(state.conflict_score, 8)
    state.confidence = round(state.confidence, 8)
    state.persistence = round(state.persistence, 8)

    after = asdict(state)

    audit_record = {
        "cycle": evidence.cycle,
        "event": "EVIDENCE_APPLIED",
        "claim_id": state.claim_id,
        "evidence": asdict(evidence),
        "independence_weight": weight,
        "weighted_value": round(weighted_value, 8),
        "state_before": before,
        "state_after": after,
        "state_digest": stable_digest(after),
    }

    return state, audit_record


def run_validation_once() -> Dict[str, object]:
    """Execute all recursive evidence cycles exactly once."""
    state = ClaimState(claim_id=CLAIM_ID, claim_text=CLAIM_TEXT)
    initial_state = asdict(state)

    history: List[Dict[str, object]] = []
    audit_log: List[Dict[str, object]] = []

    for item in EVIDENCE_SEQUENCE:
        evidence = Evidence(**item)
        state, audit = apply_evidence(state, evidence)
        audit_log.append(audit)

        history.append(
            {
                "cycle": state.cycle,
                "evidence_id": evidence.evidence_id,
                "stance": evidence.stance,
                "source": evidence.source,
                "independence_group": evidence.independence_group,
                "reliability": evidence.reliability,
                "support_score": state.support_score,
                "conflict_score": state.conflict_score,
                "confidence": state.confidence,
                "persistence": state.persistence,
                "status": state.status,
                "accepted_evidence": state.accepted_evidence,
                "support_count": state.support_count,
                "conflict_count": state.conflict_count,
                "independent_group_count": len(state.independent_groups),
                "state_digest": audit["state_digest"],
            }
        )

    deterministic_payload = {
        "test_name": TEST_NAME,
        "test_subtitle": TEST_SUBTITLE,
        "algorithm_version": ALGORITHM_VERSION,
        "schema_version": SCHEMA_VERSION,
        "initial_state": initial_state,
        "evidence_sequence": EVIDENCE_SEQUENCE,
        "history": history,
        "final_state": asdict(state),
        "audit_log": audit_log,
    }

    return {
        **deterministic_payload,
        "run_digest": stable_digest(deterministic_payload),
    }


# ======================================================================================
# 4. VALIDATION ASSERTIONS
# ======================================================================================

def evaluate_scientific_checks(result: Dict[str, object]) -> Dict[str, bool]:
    history = result["history"]
    final_state = result["final_state"]

    confidences = [row["confidence"] for row in history]
    persistence_values = [row["persistence"] for row in history]
    statuses = [row["status"] for row in history]

    return {
        # Every submitted evidence record remains in the final state.
        "all_evidence_preserved":
            len(final_state["evidence_ids"]) == len(EVIDENCE_SEQUENCE)
            and final_state["evidence_ids"]
            == [item["evidence_id"] for item in EVIDENCE_SEQUENCE],

        # Each cycle advances exactly once.
        "cycles_are_sequential":
            [row["cycle"] for row in history] == [1, 2, 3, 4],

        # Independent support in Cycle 2 should increase confidence.
        "support_reinforcement_increases_confidence":
            confidences[1] > confidences[0],

        # Credible conflict in Cycle 3 should lower confidence.
        "conflict_reduces_confidence":
            confidences[2] < confidences[1],

        # Additional support in Cycle 4 should recover confidence.
        "new_support_recovers_confidence":
            confidences[3] > confidences[2],

        # Conflict must remain preserved rather than being erased later.
        "conflict_remains_recorded":
            final_state["conflict_count"] == 1
            and final_state["conflict_score"] > 0,

        # Recursive state must be traceable with one unique digest per cycle.
        "state_history_is_traceable":
            len({row["state_digest"] for row in history}) == len(history),

        # Confidence and persistence always remain bounded.
        "metrics_are_bounded":
            all(0.0 <= value <= 1.0 for value in confidences)
            and all(0.0 <= value <= 1.0 for value in persistence_values),

        # The conflict cycle should cause an explicit contested state.
        "conflict_is_classified":
            statuses[2] == "CONTESTED",

        # Final state should recover to a supported or persistent conclusion.
        "final_state_recovers":
            statuses[3] in ("SUPPORTED", "PERSISTENT"),
    }


def run_repeatability_test(reference: Dict[str, object], runs: int) -> Dict[str, object]:
    digests = []
    for _ in range(runs):
        result = run_validation_once()
        digests.append(result["run_digest"])

    unique_digests = sorted(set(digests))
    return {
        "requested_runs": runs,
        "completed_runs": len(digests),
        "reference_digest": reference["run_digest"],
        "unique_digest_count": len(unique_digests),
        "unique_digests": unique_digests,
        "all_runs_identical": (
            len(unique_digests) == 1
            and unique_digests[0] == reference["run_digest"]
        ),
    }


# ======================================================================================
# 5. OUTPUT HELPERS
# ======================================================================================

def prepare_output_directory() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True, ensure_ascii=False)


def write_history_csv(path: Path, history: List[Dict[str, object]]) -> None:
    fieldnames = list(history[0].keys())
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(history)


def write_audit_csv(path: Path, audit_log: List[Dict[str, object]]) -> None:
    rows = []
    for record in audit_log:
        evidence = record["evidence"]
        before = record["state_before"]
        after = record["state_after"]
        rows.append(
            {
                "cycle": record["cycle"],
                "event": record["event"],
                "claim_id": record["claim_id"],
                "evidence_id": evidence["evidence_id"],
                "source": evidence["source"],
                "independence_group": evidence["independence_group"],
                "stance": evidence["stance"],
                "reliability": evidence["reliability"],
                "independence_weight": record["independence_weight"],
                "weighted_value": record["weighted_value"],
                "status_before": before["status"],
                "status_after": after["status"],
                "confidence_before": before["confidence"],
                "confidence_after": after["confidence"],
                "persistence_before": before["persistence"],
                "persistence_after": after["persistence"],
                "state_digest": record["state_digest"],
            }
        )

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def create_confidence_plot(history: List[Dict[str, object]], path: Path) -> None:
    cycles = [row["cycle"] for row in history]
    confidence = [row["confidence"] for row in history]
    persistence = [row["persistence"] for row in history]

    plt.figure(figsize=(10, 6))
    plt.plot(cycles, confidence, marker="o", linewidth=2, label="Confidence")
    plt.plot(cycles, persistence, marker="s", linewidth=2, label="Persistence")
    plt.axhline(0.65, linestyle="--", linewidth=1, label="Persistent confidence threshold")
    plt.xticks(cycles)
    plt.ylim(0, 1)
    plt.xlabel("Recursive Evidence Cycle")
    plt.ylabel("Score")
    plt.title("MPRD Claim Evolution Across Recursive Cycles")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def create_evidence_balance_plot(history: List[Dict[str, object]], path: Path) -> None:
    cycles = [row["cycle"] for row in history]
    support = [row["support_score"] for row in history]
    conflict = [row["conflict_score"] for row in history]

    plt.figure(figsize=(10, 6))
    plt.plot(cycles, support, marker="o", linewidth=2, label="Accumulated Support")
    plt.plot(cycles, conflict, marker="s", linewidth=2, label="Accumulated Conflict")
    plt.xticks(cycles)
    plt.xlabel("Recursive Evidence Cycle")
    plt.ylabel("Weighted Evidence Score")
    plt.title("Preserved Support and Conflict Evidence")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def write_text_report(
    path: Path,
    result: Dict[str, object],
    checks: Dict[str, bool],
    repeatability: Dict[str, object],
    execution_complete: bool,
    elapsed_seconds: float,
) -> None:
    scientific_pass = all(checks.values())
    final_state = result["final_state"]

    lines = [
        "=" * 100,
        TEST_NAME,
        TEST_SUBTITLE,
        "=" * 100,
        f"Algorithm version: {ALGORITHM_VERSION}",
        f"Schema version: {SCHEMA_VERSION}",
        f"Claim: {CLAIM_TEXT}",
        f"Recursive cycles: {len(EVIDENCE_SEQUENCE)}",
        f"Repeatability runs: {REPEATABILITY_RUNS}",
        "",
        "SCIENTIFIC CHECKS",
        "-" * 100,
    ]

    for name, passed in checks.items():
        lines.append(f"{name}: {'PASS' if passed else 'FAIL'}")

    lines.extend(
        [
            "",
            "FINAL CLAIM STATE",
            "-" * 100,
            f"Status: {final_state['status']}",
            f"Confidence: {final_state['confidence']:.8f}",
            f"Persistence: {final_state['persistence']:.8f}",
            f"Support score: {final_state['support_score']:.8f}",
            f"Conflict score: {final_state['conflict_score']:.8f}",
            f"Accepted evidence: {final_state['accepted_evidence']}",
            f"Independent groups: {len(final_state['independent_groups'])}",
            f"Evidence IDs: {', '.join(final_state['evidence_ids'])}",
            "",
            "REPEATABILITY",
            "-" * 100,
            f"Completed runs: {repeatability['completed_runs']}",
            f"Unique deterministic digests: {repeatability['unique_digest_count']}",
            f"All runs identical: {repeatability['all_runs_identical']}",
            f"Reference digest: {repeatability['reference_digest']}",
            "",
            "OUTCOMES",
            "-" * 100,
            f"Scientific outcome: {'PASS' if scientific_pass else 'FAIL'}",
            f"Execution completeness: {'COMPLETE' if execution_complete else 'INCOMPLETE'}",
            f"Elapsed time: {elapsed_seconds:.4f} seconds",
            "",
            "Interpretation:",
            (
                "The test supports deterministic recursive evidence integration, preservation of "
                "supporting and conflicting evidence, proportional claim-state revision, and "
                "repeatable audit-state generation."
                if scientific_pass
                else
                "One or more predefined scientific checks failed. Review the evidence history and "
                "audit log before drawing a conclusion."
            ),
            "",
            "Important scope note:",
            (
                "This validation tests the explicitly documented Test 02 mechanics implemented in "
                "this standalone harness. It does not establish performance outside the tested "
                "scenarios or prove that every future MPRD integration will behave identically."
            ),
            "=" * 100,
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


# ======================================================================================
# 6. MAIN EXECUTION
# ======================================================================================

def main() -> None:
    started = time.perf_counter()
    prepare_output_directory()

    execution_errors: List[str] = []

    try:
        result = run_validation_once()
        checks = evaluate_scientific_checks(result)
        repeatability = run_repeatability_test(result, REPEATABILITY_RUNS)

        checks["repeatability_verified"] = repeatability["all_runs_identical"]

        metadata = {
            "test_name": TEST_NAME,
            "test_subtitle": TEST_SUBTITLE,
            "algorithm_version": ALGORITHM_VERSION,
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "repeatability_runs": REPEATABILITY_RUNS,
        }

        # Core evidence files
        write_json(OUTPUT_DIR / "MPRD_Test_02_Full_Result.json", result)
        write_json(OUTPUT_DIR / "MPRD_Test_02_Audit_Log.json", result["audit_log"])
        write_json(OUTPUT_DIR / "MPRD_Test_02_Final_State.json", result["final_state"])
        write_json(OUTPUT_DIR / "MPRD_Test_02_Scientific_Checks.json", checks)
        write_json(OUTPUT_DIR / "MPRD_Test_02_Repeatability.json", repeatability)
        write_json(OUTPUT_DIR / "MPRD_Test_02_Metadata.json", metadata)

        write_history_csv(
            OUTPUT_DIR / "MPRD_Test_02_Claim_Evolution.csv",
            result["history"],
        )
        write_audit_csv(
            OUTPUT_DIR / "MPRD_Test_02_Audit_Log.csv",
            result["audit_log"],
        )

        # Figures
        create_confidence_plot(
            result["history"],
            OUTPUT_DIR / "MPRD_Test_02_Confidence_and_Persistence.png",
        )
        create_evidence_balance_plot(
            result["history"],
            OUTPUT_DIR / "MPRD_Test_02_Evidence_Balance.png",
        )

    except Exception as exc:
        execution_errors.append(f"{type(exc).__name__}: {exc}")
        result = {}
        checks = {}
        repeatability = {}

    elapsed = time.perf_counter() - started
    execution_complete = len(execution_errors) == 0

    if execution_complete:
        scientific_pass = all(checks.values())

        write_text_report(
            OUTPUT_DIR / "MPRD_Test_02_Execution_Record.txt",
            result,
            checks,
            repeatability,
            execution_complete,
            elapsed,
        )

        summary = {
            "test_name": TEST_NAME,
            "scientific_outcome": "PASS" if scientific_pass else "FAIL",
            "execution_completeness": "COMPLETE",
            "final_status": result["final_state"]["status"],
            "final_confidence": result["final_state"]["confidence"],
            "final_persistence": result["final_state"]["persistence"],
            "accepted_evidence": result["final_state"]["accepted_evidence"],
            "support_count": result["final_state"]["support_count"],
            "conflict_count": result["final_state"]["conflict_count"],
            "independent_groups": len(result["final_state"]["independent_groups"]),
            "repeatability_runs": repeatability["completed_runs"],
            "unique_digests": repeatability["unique_digest_count"],
            "run_digest": result["run_digest"],
            "elapsed_seconds": round(elapsed, 6),
        }
        write_json(OUTPUT_DIR / "MPRD_Test_02_Summary.json", summary)

        print("\n" + "=" * 100)
        print(f"{TEST_NAME}: {TEST_SUBTITLE}")
        print("=" * 100)
        print(f"Scientific outcome:       {'PASS' if scientific_pass else 'FAIL'}")
        print("Execution completeness:   COMPLETE")
        print(f"Final claim status:       {result['final_state']['status']}")
        print(f"Final confidence:         {result['final_state']['confidence']:.8f}")
        print(f"Final persistence:        {result['final_state']['persistence']:.8f}")
        print(f"Accepted evidence:        {result['final_state']['accepted_evidence']}")
        print(f"Support / conflict:       {result['final_state']['support_count']} / "
              f"{result['final_state']['conflict_count']}")
        print(f"Independent groups:       {len(result['final_state']['independent_groups'])}")
        print(f"Repeatability:            {repeatability['completed_runs']} runs, "
              f"{repeatability['unique_digest_count']} unique digest(s)")
        print(f"Run digest:               {result['run_digest']}")
        print(f"Elapsed time:             {elapsed:.4f}s")
        print("-" * 100)

        for row in result["history"]:
            print(
                f"Cycle {row['cycle']} | {row['stance'].upper():8s} | "
                f"Confidence={row['confidence']:.4f} | "
                f"Persistence={row['persistence']:.4f} | "
                f"Status={row['status']}"
            )

    else:
        error_payload = {
            "test_name": TEST_NAME,
            "scientific_outcome": "NOT EVALUATED",
            "execution_completeness": "INCOMPLETE",
            "errors": execution_errors,
            "elapsed_seconds": round(elapsed, 6),
        }
        write_json(OUTPUT_DIR / "MPRD_Test_02_Execution_Error.json", error_payload)

        print("\n" + "=" * 100)
        print(f"{TEST_NAME}: EXECUTION INCOMPLETE")
        print("=" * 100)
        for error in execution_errors:
            print(error)

    # Create one ZIP containing the complete evidence directory.
    archive_path = shutil.make_archive(
        ZIP_BASENAME,
        "zip",
        root_dir=OUTPUT_DIR.parent,
        base_dir=OUTPUT_DIR.name,
    )

    print("-" * 100)
    print(f"Evidence directory: {OUTPUT_DIR.resolve()}")
    print(f"ZIP evidence package: {Path(archive_path).resolve()}")
    print("=" * 100)

    # Automatically offer the ZIP for download when running in Google Colab.
    try:
        from google.colab import files  # type: ignore
        files.download(archive_path)
    except Exception:
        print("Automatic download is only available in Google Colab.")
        print("The ZIP package has still been created in the current working directory.")


if __name__ == "__main__":
    main()
