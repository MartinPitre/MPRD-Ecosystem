"""
MPRD_V1 Phase 1 Validation Test 04
Recursive Knowledge Evolution Validation
========================================

Martin Pitre Framework of Relational Distinction, Persistence,
and Recursive Development

Algorithm version: 1.0.1
Test date: 2026-07-29
Author: Martin Pitre

Purpose
-------
This standalone Google Colab script validates whether MPRD_V1 can evolve
knowledge states across sequential recursive cycles while preserving all
accepted evidence, handling contradiction, reaching stable convergence,
and producing deterministic state digests.

The script uses only the Python standard library and can be copied directly
into one Google Colab code cell.

Planned validation scenarios
----------------------------
1. Initial candidate claim.
2. First supporting evidence.
3. Independent confirmation.
4. Additional independent support.
5. Contradictory evidence.
6. Additional supporting evidence.
7. Recursive convergence, evidence preservation, and rejection control.
8. Repeatability and run-digest verification.
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
TEST_NAME = "MPRD_V1 Phase 1 Validation Test 04"
TEST_TITLE = "Recursive Knowledge Evolution Validation"
SCHEMA_VERSION = "1.0"
RESULTS_FILE = "MPRD_V1_Validation_Test_04_Results.json"
REPEAT_RUNS = 30
MAX_CONVERGENCE_CYCLES = 20


class ValidationError(Exception):
    """Raised when an evidence record or configuration violates the test contract."""


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
        if isinstance(self.cycle, bool) or not isinstance(self.cycle, int) or self.cycle < 1:
            raise ValidationError("cycle must be an integer of at least 1.")

        for name, value in (("quality", self.quality), ("reliability", self.reliability)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError(f"{name} must be numeric.")
            if not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
                raise ValidationError(f"{name} must be between 0.0 and 1.0.")

        try:
            relation = RelationType(self.relation)
        except ValueError as exc:
            raise ValidationError("relation must be support or contradiction.") from exc

        return EvidenceRecord(
            evidence_id=evidence_id,
            source_id=source_id,
            independence_group=independence_group,
            relation=relation,
            quality=float(self.quality),
            reliability=float(self.reliability),
            cycle=self.cycle,
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
        if not (
            0.0
            <= self.rejection_threshold
            < self.support_threshold
            <= self.persistence_threshold
            <= 1.0
        ):
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
    evidence_count: int
    independent_groups: int
    support_score: float
    contradiction_score: float
    adjusted_support: float
    confidence: float
    persistence: float
    evidence_preserved: bool
    state_digest: str
    notes: Tuple[str, ...]


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
    """Compute one deterministic claim state using the validated v1.0.1 rules."""
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

    mean_support = (
        sum(support_strengths) / len(support_strengths)
        if support_strengths
        else 0.0
    )
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
            (len(supports) - len(contradictions) + len(visible))
            / (2.0 * len(visible))
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
            "Contradictory evidence remains materially present, so the claim is contested."
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
            "The support threshold and independent confirmation requirements were satisfied."
        )

    elif adjusted_support < config.rejection_threshold and contradictions:
        status = ClaimStatus.REJECTED
        rationale.append("Adjusted support fell below the rejection threshold.")

    else:
        status = ClaimStatus.CANDIDATE
        rationale.append(
            "Evidence has been integrated, but the support requirements remain incomplete."
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


def build_evolution_packet() -> List[EvidenceRecord]:
    """Sequential evidence packet for the primary knowledge-evolution claim."""
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
            notes="Independent confirmation.",
        ),
        EvidenceRecord(
            evidence_id="E3",
            source_id="source_gamma",
            independence_group="group_gamma",
            relation=RelationType.SUPPORT,
            quality=0.98,
            reliability=0.98,
            cycle=3,
            notes="Additional strong independent support.",
        ),
        EvidenceRecord(
            evidence_id="E4",
            source_id="source_delta",
            independence_group="group_delta",
            relation=RelationType.CONTRADICTION,
            quality=0.62,
            reliability=0.66,
            cycle=4,
            notes="Moderate contradictory observation.",
        ),
        EvidenceRecord(
            evidence_id="E5",
            source_id="source_epsilon",
            independence_group="group_epsilon",
            relation=RelationType.SUPPORT,
            quality=0.95,
            reliability=0.94,
            cycle=5,
            notes="Further independent support after contradiction.",
        ),
    ]


def build_rejection_control_packet() -> List[EvidenceRecord]:
    """Control packet verifying that contradiction-dominant evidence can be rejected."""
    return [
        EvidenceRecord(
            evidence_id="R1",
            source_id="control_support",
            independence_group="control_group_support",
            relation=RelationType.SUPPORT,
            quality=0.20,
            reliability=0.25,
            cycle=1,
            notes="Weak supporting control observation.",
        ),
        EvidenceRecord(
            evidence_id="R2",
            source_id="control_contradiction",
            independence_group="control_group_contradiction",
            relation=RelationType.CONTRADICTION,
            quality=0.98,
            reliability=0.99,
            cycle=2,
            notes="Strong contradictory control observation.",
        ),
    ]


def evidence_preserved(previous: ClaimState, current: ClaimState) -> bool:
    """Every evidence ID previously accepted must remain in the next state."""
    return set(previous.evidence_ids).issubset(set(current.evidence_ids))


def converge_claim_state(
    evidence: Sequence[EvidenceRecord],
    starting_cycle: int,
    config: MPRDConfig,
    max_cycles: int = MAX_CONVERGENCE_CYCLES,
) -> Tuple[ClaimState, int, Tuple[str, ...]]:
    """
    Re-evaluate an unchanged evidence state until two consecutive substantive
    state digests are identical. Cycle metadata is held constant because no new
    evidence has been introduced.
    """
    digest_history: List[str] = []
    previous: ClaimState | None = None

    for iteration in range(1, max_cycles + 1):
        current = compute_claim_state(evidence, cycle=starting_cycle, config=config)
        digest_history.append(current.digest)

        if previous is not None and current == previous:
            return current, iteration, tuple(digest_history)

        previous = current

    raise RuntimeError(
        f"Convergence was not reached within {max_cycles} recursive evaluations."
    )


def make_scenario(
    scenario_id: int,
    title: str,
    expected: ClaimStatus,
    state: ClaimState,
    preservation_ok: bool,
    extra_notes: Sequence[str] = (),
) -> ScenarioResult:
    passed = state.status == expected and preservation_ok
    return ScenarioResult(
        scenario_id=scenario_id,
        title=title,
        expected_status=expected.value,
        observed_status=state.status.value,
        passed=passed,
        evidence_count=state.evidence_count,
        independent_groups=state.independent_groups,
        support_score=state.support_score,
        contradiction_score=state.contradiction_score,
        adjusted_support=state.adjusted_support,
        confidence=state.confidence,
        persistence=state.persistence,
        evidence_preserved=preservation_ok,
        state_digest=state.digest,
        notes=tuple(state.rationale) + tuple(extra_notes),
    )


def run_once() -> Dict[str, object]:
    config = MPRDConfig().validated()
    packet = build_evolution_packet()

    state_0 = compute_claim_state([], cycle=0, config=config)
    state_1 = compute_claim_state(packet, cycle=1, config=config)
    state_2 = compute_claim_state(packet, cycle=2, config=config)
    state_3 = compute_claim_state(packet, cycle=3, config=config)
    state_4 = compute_claim_state(packet, cycle=4, config=config)
    state_5 = compute_claim_state(packet, cycle=5, config=config)

    scenarios: List[ScenarioResult] = [
        make_scenario(
            1,
            "Initial candidate claim",
            ClaimStatus.CANDIDATE,
            state_0,
            preservation_ok=True,
        ),
        make_scenario(
            2,
            "First supporting evidence",
            ClaimStatus.INSUFFICIENT,
            state_1,
            preservation_ok=evidence_preserved(state_0, state_1),
        ),
        make_scenario(
            3,
            "Independent confirmation",
            ClaimStatus.SUPPORTED,
            state_2,
            preservation_ok=evidence_preserved(state_1, state_2),
        ),
        make_scenario(
            4,
            "Additional independent support",
            ClaimStatus.PERSISTENT,
            state_3,
            preservation_ok=evidence_preserved(state_2, state_3),
        ),
        make_scenario(
            5,
            "Contradictory evidence",
            ClaimStatus.CONTESTED,
            state_4,
            preservation_ok=evidence_preserved(state_3, state_4),
        ),
        make_scenario(
            6,
            "Additional supporting evidence",
            ClaimStatus.CONTESTED,
            state_5,
            preservation_ok=evidence_preserved(state_4, state_5),
            extra_notes=(
                "The contradictory record remained preserved rather than being discarded.",
                "Additional support increased the evidence base without corrupting traceability.",
            ),
        ),
    ]

    converged_state, convergence_iterations, convergence_digests = converge_claim_state(
        packet,
        starting_cycle=5,
        config=config,
    )

    rejection_packet = build_rejection_control_packet()
    rejection_state = compute_claim_state(
        rejection_packet,
        cycle=2,
        config=config,
    )

    convergence_ok = (
        converged_state == state_5
        and len(set(convergence_digests)) == 1
        and convergence_iterations == 2
    )
    rejection_ok = rejection_state.status == ClaimStatus.REJECTED
    scenario_7_pass = convergence_ok and rejection_ok

    scenarios.append(
        ScenarioResult(
            scenario_id=7,
            title="Recursive convergence and rejection control",
            expected_status=(
                f"{state_5.status.value} convergence; "
                f"control={ClaimStatus.REJECTED.value}"
            ),
            observed_status=(
                f"{converged_state.status.value} convergence; "
                f"control={rejection_state.status.value}"
            ),
            passed=scenario_7_pass,
            evidence_count=converged_state.evidence_count,
            independent_groups=converged_state.independent_groups,
            support_score=converged_state.support_score,
            contradiction_score=converged_state.contradiction_score,
            adjusted_support=converged_state.adjusted_support,
            confidence=converged_state.confidence,
            persistence=converged_state.persistence,
            evidence_preserved=set(state_5.evidence_ids)
            == set(converged_state.evidence_ids),
            state_digest=converged_state.digest,
            notes=(
                f"Convergence reached after {convergence_iterations} evaluations.",
                f"Unique convergence digests: {len(set(convergence_digests))}.",
                "The unchanged primary evidence state produced an identical claim state.",
                f"Rejection control status: {rejection_state.status.value}.",
                f"Rejection control digest: {rejection_state.digest}.",
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
        "primary_evidence_packet": [
            {**asdict(record), "relation": record.relation.value}
            for record in packet
        ],
        "rejection_control_packet": [
            {**asdict(record), "relation": record.relation.value}
            for record in rejection_packet
        ],
        "scenario_results": [asdict(result) for result in scenarios],
        "primary_final_state": {
            **asdict(converged_state),
            "status": converged_state.status.value,
        },
        "rejection_control_state": {
            **asdict(rejection_state),
            "status": rejection_state.status.value,
        },
        "convergence": {
            "iterations": convergence_iterations,
            "digest_history": list(convergence_digests),
            "unique_digest_count": len(set(convergence_digests)),
            "stable": convergence_ok,
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


def print_state_metrics(item: Dict[str, object]) -> None:
    print(
        f"  Evidence={item['evidence_count']} | "
        f"Independent groups={item['independent_groups']} | "
        f"Preserved={'YES' if item['evidence_preserved'] else 'NO'}"
    )
    print(
        f"  Support={item['support_score']:.6f} | "
        f"Contradiction={item['contradiction_score']:.6f} | "
        f"Adjusted={item['adjusted_support']:.6f}"
    )
    print(
        f"  Confidence={item['confidence']:.6f} | "
        f"Persistence={item['persistence']:.6f}"
    )
    print(f"  State digest: {item['state_digest']}")


def print_report(result: Dict[str, object], elapsed_seconds: float) -> None:
    reference = result["reference_run"]
    scenarios = reference["scenario_results"]
    passed = sum(bool(item["passed"]) for item in scenarios)
    total = len(scenarios)

    scenario_checks_pass = passed == total
    repeatability_pass = bool(result["deterministic"])
    overall_pass = scenario_checks_pass and repeatability_pass

    print("=" * 108)
    print(TEST_NAME)
    print(TEST_TITLE)
    print("=" * 108)
    print(f"Algorithm: {ALGORITHM_NAME} v{ALGORITHM_VERSION}")
    print(f"Scientific outcome: {'PASS' if overall_pass else 'FAIL'}")
    print("Execution completeness: COMPLETE")
    print(f"Core scenarios passed: {passed}/{total}")
    print(
        f"Repeatability: {result['runs']} runs, "
        f"{result['unique_digest_count']} unique digest(s)"
    )
    print(f"Deterministic: {'YES' if result['deterministic'] else 'NO'}")
    print(f"Run digest: {reference['run_digest']}")
    print(f"Elapsed time: {elapsed_seconds:.4f}s")
    print("-" * 108)

    for item in scenarios:
        print(
            f"Scenario {item['scenario_id']:02d} | "
            f"{'PASS' if item['passed'] else 'FAIL'} | "
            f"{item['title']}"
        )
        print(
            f"  Expected={item['expected_status']} | "
            f"Observed={item['observed_status']}"
        )
        print_state_metrics(item)
        for note in item["notes"]:
            print(f"  - {note}")
        print("-" * 108)

    print("Scenario 08 | "
          f"{'PASS' if repeatability_pass else 'FAIL'} | "
          "Repeatability and run-digest verification")
    print(
        f"  Runs={result['runs']} | "
        f"Unique digests={result['unique_digest_count']} | "
        f"Deterministic={'YES' if result['deterministic'] else 'NO'}"
    )
    for digest in result["unique_digests"]:
        print(f"  Run digest: {digest}")
    print("-" * 108)

    final_state = reference["primary_final_state"]
    rejection_state = reference["rejection_control_state"]
    convergence = reference["convergence"]

    print("FINAL PRIMARY KNOWLEDGE STATE")
    print(f"Status: {final_state['status']}")
    print(f"Evidence integrated: {final_state['evidence_count']}")
    print(
        f"Support / contradiction: "
        f"{final_state['support_count']} / {final_state['contradiction_count']}"
    )
    print(f"Independent groups: {final_state['independent_groups']}")
    print(f"Support score: {final_state['support_score']:.8f}")
    print(f"Contradiction score: {final_state['contradiction_score']:.8f}")
    print(f"Adjusted support: {final_state['adjusted_support']:.8f}")
    print(f"Confidence: {final_state['confidence']:.8f}")
    print(f"Persistence: {final_state['persistence']:.8f}")
    print(f"State digest: {final_state['digest']}")
    print(
        f"Convergence: {'STABLE' if convergence['stable'] else 'UNSTABLE'} | "
        f"Evaluations={convergence['iterations']} | "
        f"Unique convergence digests={convergence['unique_digest_count']}"
    )
    print("-" * 108)
    print("REJECTION CONTROL STATE")
    print(f"Status: {rejection_state['status']}")
    print(f"Adjusted support: {rejection_state['adjusted_support']:.8f}")
    print(f"Contradiction score: {rejection_state['contradiction_score']:.8f}")
    print(f"State digest: {rejection_state['digest']}")
    print("=" * 108)


def main() -> None:
    start = time.perf_counter()
    repeatability = run_repeatability_test(REPEAT_RUNS)
    elapsed = time.perf_counter() - start

    reference = repeatability["reference_run"]
    scenarios = reference["scenario_results"]
    core_passed = sum(bool(item["passed"]) for item in scenarios)
    core_total = len(scenarios)
    repeatability_pass = bool(repeatability["deterministic"])
    overall_pass = core_passed == core_total and repeatability_pass

    output = {
        "test_name": TEST_NAME,
        "test_title": TEST_TITLE,
        "algorithm_name": ALGORITHM_NAME,
        "algorithm_version": ALGORITHM_VERSION,
        "schema_version": SCHEMA_VERSION,
        "scientific_outcome": "PASS" if overall_pass else "FAIL",
        "execution_completeness": "COMPLETE",
        "scenario_summary": {
            "core_scenarios_passed": core_passed,
            "core_scenarios_total": core_total,
            "repeatability_scenario_passed": repeatability_pass,
            "total_planned_scenarios": 8,
        },
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
