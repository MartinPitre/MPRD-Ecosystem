"""
MPRD_V1 Phase 1 Validation Test 03
Recursive Evidence Integration Validation
=========================================

Martin Pitre Framework of Relational Distinction, Persistence,
and Recursive Development

Version: 1.0
Author: Martin Pitre
Date: 2026-07-29

Purpose
-------
This standalone Google Colab script validates whether MPRD_V1 can integrate
supporting and contradicting evidence across successive recursive processing
cycles while preserving deterministic, traceable, and reproducible claim-state
updates.

The script uses only the Python standard library and may be copied directly
into one Google Colab cell.

Validation focus
----------------
1. Initial claim creation.
2. First supporting evidence.
3. Independent supporting confirmation.
4. Contradictory evidence integration.
5. Additional supporting evidence.
6. Recursive re-evaluation.
7. Final claim-state assessment.
8. Repeatability and digest verification.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List, Sequence, Tuple


ALGORITHM_NAME = "MPRD_V1 Core Algorithm"
ALGORITHM_VERSION = "1.0.1"
TEST_NAME = "MPRD_V1 Phase 1 Validation Test 03"
TEST_TITLE = "Recursive Evidence Integration Validation"
SCHEMA_VERSION = "1.0"
RESULTS_FILE = "MPRD_V1_Validation_Test_03_Results.json"
REPEAT_RUNS = 30


class ValidationError(Exception):
    """Raised when an evidence record violates the test contract."""


class RelationType(str, Enum):
    SUPPORT = "support"
    CONTRADICTION = "contradiction"


class ClaimStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    SUPPORTED = "SUPPORTED"
    PERSISTENT = "PERSISTENT"
    CONTESTED = "CONTESTED"
    REJECTED = "REJECTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source_id: str
    independence_group: str
    relation: RelationType
    quality: float
    reliability: float
    cycle: int
    notes: str = ""

    def validated(self) -> "EvidenceRecord":
        evidence_id = self.evidence_id.strip()
        source_id = self.source_id.strip()
        independence_group = self.independence_group.strip()

        if not evidence_id:
            raise ValidationError("evidence_id must not be empty.")
        if not source_id:
            raise ValidationError("source_id must not be empty.")
        if not independence_group:
            raise ValidationError("independence_group must not be empty.")
        if self.cycle < 1:
            raise ValidationError("cycle must be at least 1.")

        for name, value in (("quality", self.quality), ("reliability", self.reliability)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError(f"{name} must be numeric.")
            if not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
                raise ValidationError(f"{name} must be between 0.0 and 1.0.")

        return EvidenceRecord(
            evidence_id=evidence_id,
            source_id=source_id,
            independence_group=independence_group,
            relation=RelationType(self.relation),
            quality=float(self.quality),
            reliability=float(self.reliability),
            cycle=int(self.cycle),
            notes=self.notes.strip(),
        )


@dataclass(frozen=True)
class MPRDConfig:
    support_threshold: float = 0.60
    persistence_threshold: float = 0.75
    rejection_threshold: float = 0.25
    contradiction_contested_threshold: float = 0.20
    contradiction_penalty: float = 0.65
    evidence_weight: float = 0.45
    independence_weight: float = 0.20
    recurrence_weight: float = 0.15
    relational_weight: float = 0.20
    minimum_independent_groups_for_support: int = 2
    minimum_independent_groups_for_persistence: int = 2
    minimum_records_for_persistence: int = 2

    def validated(self) -> "MPRDConfig":
        weights = (
            self.evidence_weight,
            self.independence_weight,
            self.recurrence_weight,
            self.relational_weight,
        )
        if not math.isclose(sum(weights), 1.0, abs_tol=1e-12):
            raise ValidationError("Scoring weights must total 1.0.")
        if not 0.0 <= self.rejection_threshold < self.support_threshold <= self.persistence_threshold <= 1.0:
            raise ValidationError("Threshold ordering is invalid.")
        return self


@dataclass(frozen=True)
class ClaimState:
    cycle: int
    evidence_count: int
    support_count: int
    contradiction_count: int
    independent_groups: int
    support_score: float
    contradiction_score: float
    adjusted_support: float
    confidence: float
    persistence: float
    status: ClaimStatus
    evidence_ids: Tuple[str, ...]
    rationale: Tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: int
    title: str
    expected_status: str
    observed_status: str
    passed: bool
    support_score: float
    contradiction_score: float
    confidence: float
    persistence: float
    independent_groups: int
    evidence_count: int
    state_digest: str
    rationale: Tuple[str, ...]


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def stable_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evidence_strength(record: EvidenceRecord) -> float:
    return math.sqrt(record.quality * record.reliability)


def compute_claim_state(
    evidence: Sequence[EvidenceRecord],
    cycle: int,
    config: MPRDConfig,
) -> ClaimState:
    config.validated()

    validated = [record.validated() for record in evidence]
    ids = [record.evidence_id for record in validated]
    if len(ids) != len(set(ids)):
        raise ValidationError("Duplicate evidence_id detected.")

    visible = sorted(
        (record for record in validated if record.cycle <= cycle),
        key=lambda record: (record.cycle, record.evidence_id),
    )

    supports = [r for r in visible if r.relation == RelationType.SUPPORT]
    contradictions = [r for r in visible if r.relation == RelationType.CONTRADICTION]

    support_strengths = [evidence_strength(r) for r in supports]
    contradiction_strengths = [evidence_strength(r) for r in contradictions]

    mean_support = sum(support_strengths) / len(support_strengths) if support_strengths else 0.0
    mean_contradiction = (
        sum(contradiction_strengths) / len(contradiction_strengths)
        if contradiction_strengths
        else 0.0
    )

    independent_groups = len({r.independence_group for r in supports})
    recurrence_count = len(supports)

    independence_component = clamp(independent_groups / 3.0)
    recurrence_component = clamp(recurrence_count / 4.0)

    if visible:
        relation_balance = clamp(
            (len(supports) - len(contradictions) + len(visible)) /
            (2.0 * len(visible))
        )
    else:
        relation_balance = 0.0

    support_score = clamp(
        config.evidence_weight * mean_support
        + config.independence_weight * independence_component
        + config.recurrence_weight * recurrence_component
        + config.relational_weight * relation_balance
    )

    contradiction_score = clamp(mean_contradiction)
    adjusted_support = clamp(
        support_score - config.contradiction_penalty * contradiction_score
    )

    confidence = clamp(
        0.70 * adjusted_support
        + 0.20 * independence_component
        + 0.10 * recurrence_component
    )

    persistence = clamp(
        0.55 * adjusted_support
        + 0.25 * independence_component
        + 0.20 * recurrence_component
    )

    rationale: List[str] = []

    if not visible:
        status = ClaimStatus.CANDIDATE
        rationale.append("No evidence has yet been integrated.")

    elif len(supports) == 1 and independent_groups == 1 and not contradictions:
        status = ClaimStatus.INSUFFICIENT
        rationale.append(
            "A single supporting record without independent confirmation remains insufficient."
        )

    elif contradiction_score >= 0.85 and adjusted_support < config.rejection_threshold:
        status = ClaimStatus.REJECTED
        rationale.append(
            "Strong contradiction combined with low adjusted support triggered rejection."
        )

    elif contradictions and contradiction_score >= config.contradiction_contested_threshold:
        status = ClaimStatus.CONTESTED
        rationale.append(
            "Contradictory evidence is materially present and the claim is contested."
        )

    elif (
        adjusted_support >= config.support_threshold
        and persistence >= config.persistence_threshold
        and independent_groups >= config.minimum_independent_groups_for_persistence
        and len(supports) >= config.minimum_records_for_persistence
    ):
        status = ClaimStatus.PERSISTENT
        rationale.append(
            "Support, persistence, independence, and recurrence requirements were satisfied."
        )

    elif (
        adjusted_support >= config.support_threshold
        and independent_groups >= config.minimum_independent_groups_for_support
    ):
        status = ClaimStatus.SUPPORTED
        rationale.append(
            "The ordinary support threshold and independent confirmation requirements were satisfied."
        )

    elif adjusted_support < config.rejection_threshold and contradictions:
        status = ClaimStatus.REJECTED
        rationale.append(
            "Adjusted support fell below the rejection threshold."
        )

    else:
        status = ClaimStatus.CANDIDATE
        rationale.append(
            "Evidence has been integrated, but support requirements remain incomplete."
        )

    if supports:
        rationale.append(f"{len(supports)} supporting evidence record(s) integrated.")
    if contradictions:
        rationale.append(f"{len(contradictions)} contradicting evidence record(s) integrated.")
    rationale.append(f"{independent_groups} independent supporting group(s) represented.")

    digest_payload = {
        "cycle": cycle,
        "evidence_ids": [r.evidence_id for r in visible],
        "support_count": len(supports),
        "contradiction_count": len(contradictions),
        "independent_groups": independent_groups,
        "support_score": round(support_score, 12),
        "contradiction_score": round(contradiction_score, 12),
        "adjusted_support": round(adjusted_support, 12),
        "confidence": round(confidence, 12),
        "persistence": round(persistence, 12),
        "status": status.value,
        "rationale": rationale,
    }

    return ClaimState(
        cycle=cycle,
        evidence_count=len(visible),
        support_count=len(supports),
        contradiction_count=len(contradictions),
        independent_groups=independent_groups,
        support_score=round(support_score, 8),
        contradiction_score=round(contradiction_score, 8),
        adjusted_support=round(adjusted_support, 8),
        confidence=round(confidence, 8),
        persistence=round(persistence, 8),
        status=status,
        evidence_ids=tuple(r.evidence_id for r in visible),
        rationale=tuple(rationale),
        digest=stable_digest(digest_payload),
    )


def build_evidence_packet() -> List[EvidenceRecord]:
    return [
        EvidenceRecord(
            evidence_id="E1",
            source_id="source_alpha",
            independence_group="group_alpha",
            relation=RelationType.SUPPORT,
            quality=0.88,
            reliability=0.90,
            cycle=1,
            notes="First supporting observation.",
        ),
        EvidenceRecord(
            evidence_id="E2",
            source_id="source_beta",
            independence_group="group_beta",
            relation=RelationType.SUPPORT,
            quality=0.92,
            reliability=0.91,
            cycle=2,
            notes="Independent supporting confirmation.",
        ),
        EvidenceRecord(
            evidence_id="E3",
            source_id="source_gamma",
            independence_group="group_gamma",
            relation=RelationType.CONTRADICTION,
            quality=0.62,
            reliability=0.66,
            cycle=3,
            notes="Moderate contradictory observation.",
        ),
        EvidenceRecord(
            evidence_id="E4",
            source_id="source_delta",
            independence_group="group_delta",
            relation=RelationType.SUPPORT,
            quality=0.95,
            reliability=0.94,
            cycle=4,
            notes="Additional strong independent support.",
        ),
        EvidenceRecord(
            evidence_id="E5",
            source_id="source_epsilon",
            independence_group="group_epsilon",
            relation=RelationType.SUPPORT,
            quality=0.91,
            reliability=0.93,
            cycle=5,
            notes="Further independent recurrence.",
        ),
    ]


def run_once() -> Dict[str, object]:
    config = MPRDConfig().validated()
    packet = build_evidence_packet()

    states = [
        compute_claim_state([], cycle=0, config=config),
        compute_claim_state(packet, cycle=1, config=config),
        compute_claim_state(packet, cycle=2, config=config),
        compute_claim_state(packet, cycle=3, config=config),
        compute_claim_state(packet, cycle=4, config=config),
        compute_claim_state(packet, cycle=5, config=config),
    ]

    expected = [
        ClaimStatus.CANDIDATE,
        ClaimStatus.INSUFFICIENT,
        ClaimStatus.SUPPORTED,
        ClaimStatus.CONTESTED,
        ClaimStatus.CONTESTED,
        ClaimStatus.CONTESTED,
    ]

    titles = [
        "Initial claim creation",
        "First supporting evidence",
        "Independent supporting confirmation",
        "Contradictory evidence integration",
        "Additional supporting evidence",
        "Recursive final-state evaluation",
    ]

    scenarios: List[ScenarioResult] = []
    for index, (title, state, expected_status) in enumerate(
        zip(titles, states, expected),
        start=1,
    ):
        scenarios.append(
            ScenarioResult(
                scenario_id=index,
                title=title,
                expected_status=expected_status.value,
                observed_status=state.status.value,
                passed=state.status == expected_status,
                support_score=state.support_score,
                contradiction_score=state.contradiction_score,
                confidence=state.confidence,
                persistence=state.persistence,
                independent_groups=state.independent_groups,
                evidence_count=state.evidence_count,
                state_digest=state.digest,
                rationale=state.rationale,
            )
        )

    # Scenario 7: verify that re-processing the same final evidence state is stable.
    final_state_a = compute_claim_state(packet, cycle=5, config=config)
    final_state_b = compute_claim_state(packet, cycle=5, config=config)
    convergence_pass = final_state_a == final_state_b

    scenarios.append(
        ScenarioResult(
            scenario_id=7,
            title="Stable recursive re-evaluation",
            expected_status=final_state_a.status.value,
            observed_status=final_state_b.status.value,
            passed=convergence_pass,
            support_score=final_state_b.support_score,
            contradiction_score=final_state_b.contradiction_score,
            confidence=final_state_b.confidence,
            persistence=final_state_b.persistence,
            independent_groups=final_state_b.independent_groups,
            evidence_count=final_state_b.evidence_count,
            state_digest=final_state_b.digest,
            rationale=(
                "The same evidence state was reprocessed without modification.",
                "All state fields and the digest remained identical.",
            ),
        )
    )

    execution_payload = {
        "algorithm_name": ALGORITHM_NAME,
        "algorithm_version": ALGORITHM_VERSION,
        "test_name": TEST_NAME,
        "test_title": TEST_TITLE,
        "schema_version": SCHEMA_VERSION,
        "config": asdict(config),
        "evidence_packet": [
            {
                **asdict(record),
                "relation": record.relation.value,
            }
            for record in packet
        ],
        "scenario_results": [asdict(result) for result in scenarios],
        "final_state": {
            **asdict(final_state_a),
            "status": final_state_a.status.value,
        },
    }
    execution_payload["run_digest"] = stable_digest(execution_payload)
    return execution_payload


def run_repeatability_test(repeats: int = REPEAT_RUNS) -> Dict[str, object]:
    runs = [run_once() for _ in range(repeats)]
    digests = [run["run_digest"] for run in runs]
    unique_digests = sorted(set(digests))

    return {
        "runs": repeats,
        "unique_digest_count": len(unique_digests),
        "unique_digests": unique_digests,
        "deterministic": len(unique_digests) == 1,
        "reference_run": runs[0],
    }


def print_report(result: Dict[str, object], elapsed_seconds: float) -> None:
    reference = result["reference_run"]
    scenarios = reference["scenario_results"]
    passed = sum(bool(item["passed"]) for item in scenarios)
    total = len(scenarios)
    overall_pass = passed == total and bool(result["deterministic"])

    print("=" * 100)
    print(TEST_NAME)
    print(TEST_TITLE)
    print("=" * 100)
    print(f"Algorithm: {ALGORITHM_NAME} v{ALGORITHM_VERSION}")
    print(f"Scientific outcome: {'PASS' if overall_pass else 'FAIL'}")
    print("Execution completeness: COMPLETE")
    print(f"Scenarios passed: {passed}/{total}")
    print(
        f"Repeatability: {result['runs']} runs, "
        f"{result['unique_digest_count']} unique digest(s)"
    )
    print(f"Deterministic: {'YES' if result['deterministic'] else 'NO'}")
    print(f"Run digest: {reference['run_digest']}")
    print(f"Elapsed time: {elapsed_seconds:.4f}s")
    print("-" * 100)

    for item in scenarios:
        print(
            f"Scenario {item['scenario_id']:02d} | "
            f"{'PASS' if item['passed'] else 'FAIL'} | "
            f"{item['title']}"
        )
        print(
            f"  Expected={item['expected_status']} | "
            f"Observed={item['observed_status']} | "
            f"Evidence={item['evidence_count']} | "
            f"Independent groups={item['independent_groups']}"
        )
        print(
            f"  Support={item['support_score']:.6f} | "
            f"Contradiction={item['contradiction_score']:.6f} | "
            f"Confidence={item['confidence']:.6f} | "
            f"Persistence={item['persistence']:.6f}"
        )
        print(f"  State digest: {item['state_digest']}")
        for rationale in item["rationale"]:
            print(f"  - {rationale}")
        print("-" * 100)

    final_state = reference["final_state"]
    print("FINAL CLAIM STATE")
    print(f"Status: {final_state['status']}")
    print(f"Evidence integrated: {final_state['evidence_count']}")
    print(f"Support / contradiction: {final_state['support_count']} / {final_state['contradiction_count']}")
    print(f"Independent groups: {final_state['independent_groups']}")
    print(f"Support score: {final_state['support_score']:.8f}")
    print(f"Contradiction score: {final_state['contradiction_score']:.8f}")
    print(f"Adjusted support: {final_state['adjusted_support']:.8f}")
    print(f"Confidence: {final_state['confidence']:.8f}")
    print(f"Persistence: {final_state['persistence']:.8f}")
    print(f"State digest: {final_state['digest']}")
    print("=" * 100)


def main() -> None:
    start = time.perf_counter()
    repeatability = run_repeatability_test(REPEAT_RUNS)
    elapsed = time.perf_counter() - start

    reference = repeatability["reference_run"]
    scenarios = reference["scenario_results"]
    passed = sum(bool(item["passed"]) for item in scenarios)
    overall_pass = passed == len(scenarios) and repeatability["deterministic"]

    output = {
        "test_name": TEST_NAME,
        "test_title": TEST_TITLE,
        "algorithm_name": ALGORITHM_NAME,
        "algorithm_version": ALGORITHM_VERSION,
        "schema_version": SCHEMA_VERSION,
        "scientific_outcome": "PASS" if overall_pass else "FAIL",
        "execution_completeness": "COMPLETE",
        "elapsed_seconds": round(elapsed, 8),
        "repeatability": {
            "runs": repeatability["runs"],
            "unique_digest_count": repeatability["unique_digest_count"],
            "unique_digests": repeatability["unique_digests"],
            "deterministic": repeatability["deterministic"],
        },
        "results": reference,
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print_report(repeatability, elapsed)
    print(f"\nJSON results saved to: {RESULTS_FILE}")

    try:
        from google.colab import files
        files.download(RESULTS_FILE)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
