# ==================================================================================================
# MPRD_V1 Phase 1 Validation Test 05
# Integrated System Integrity and Auditability Validation
#
# Algorithm: MPRD_V1 Core Algorithm v1.0.1
# Environment: Google Colab / standard Python 3
# Dependencies: Python standard library only
#
# Instructions:
# 1. Open a new Google Colab notebook.
# 2. Paste this entire script into one code cell.
# 3. Run the cell.
# 4. Download the generated JSON and TXT records from the Colab Files panel.
# ==================================================================================================

from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


ALGORITHM_NAME = "MPRD_V1 Core Algorithm v1.0.1"
TEST_NAME = "MPRD_V1 Phase 1 Validation Test 05"
TEST_SUBTITLE = "Integrated System Integrity and Auditability Validation"
REPEAT_RUNS = 30

VALID_POLARITIES = {"SUPPORT", "CONTRADICTION"}
VALID_RELATION_TYPES = {"SUPPORTS", "CONTRADICTS", "RELATED_TO"}

STATUS_CANDIDATE = "CANDIDATE"
STATUS_SUPPORTED = "SUPPORTED"
STATUS_PERSISTENT = "PERSISTENT"
STATUS_CONTESTED = "CONTESTED"
STATUS_REJECTED = "REJECTED"


# --------------------------------------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    claim_id: str
    polarity: str
    strength: float
    reliability: float
    group_id: str
    description: str

    @property
    def weight(self) -> float:
        return round(self.strength * self.reliability, 12)


@dataclass(frozen=True)
class Relation:
    relation_id: str
    source_id: str
    target_id: str
    relation_type: str
    strength: float


@dataclass
class Claim:
    claim_id: str
    text: str
    status: str = STATUS_CANDIDATE
    support: float = 0.0
    contradiction: float = 0.0
    adjusted_support: float = 0.0
    confidence: float = 0.0
    persistence: float = 0.0
    independent_groups: int = 0
    evidence_ids: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AuditRecord:
    sequence: int
    operation: str
    outcome: str
    reason: str
    target_id: str
    state_digest_before: str
    state_digest_after: str


# --------------------------------------------------------------------------------------------------
# Deterministic MPRD_V1 validation engine
# --------------------------------------------------------------------------------------------------

class MPRDValidationEngine:
    def __init__(self) -> None:
        self.claims: Dict[str, Claim] = {}
        self.evidence: Dict[str, Evidence] = {}
        self.relations: Dict[str, Relation] = {}
        self.audit: List[AuditRecord] = []
        self.sequence = 0
        self.last_termination_reason = "NOT_RUN"

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _hash(value: Any) -> str:
        return hashlib.sha256(MPRDValidationEngine._canonical_json(value).encode("utf-8")).hexdigest()

    def normalized_state(self, include_audit: bool = True) -> Dict[str, Any]:
        claims = {}
        for claim_id in sorted(self.claims):
            claim = self.claims[claim_id]
            claims[claim_id] = {
                "claim_id": claim.claim_id,
                "text": claim.text,
                "status": claim.status,
                "support": round(claim.support, 8),
                "contradiction": round(claim.contradiction, 8),
                "adjusted_support": round(claim.adjusted_support, 8),
                "confidence": round(claim.confidence, 8),
                "persistence": round(claim.persistence, 8),
                "independent_groups": claim.independent_groups,
                "evidence_ids": sorted(claim.evidence_ids),
                "history": copy.deepcopy(claim.history),
            }

        evidence = {
            evidence_id: asdict(self.evidence[evidence_id])
            for evidence_id in sorted(self.evidence)
        }
        relations = {
            relation_id: asdict(self.relations[relation_id])
            for relation_id in sorted(self.relations)
        }

        state = {
            "claims": claims,
            "evidence": evidence,
            "relations": relations,
            "last_termination_reason": self.last_termination_reason,
        }

        if include_audit:
            state["audit"] = [asdict(record) for record in self.audit]
        return state

    def state_digest(self, include_audit: bool = True) -> str:
        return self._hash(self.normalized_state(include_audit=include_audit))

    def _record(
        self,
        operation: str,
        outcome: str,
        reason: str,
        target_id: str,
        before: str,
        after: str,
    ) -> None:
        self.sequence += 1
        self.audit.append(
            AuditRecord(
                sequence=self.sequence,
                operation=operation,
                outcome=outcome,
                reason=reason,
                target_id=target_id,
                state_digest_before=before,
                state_digest_after=after,
            )
        )

    def create_claim(self, claim_id: str, text: str) -> Tuple[bool, str]:
        before = self.state_digest()
        if not isinstance(claim_id, str) or not claim_id.strip():
            after = self.state_digest()
            self._record("CREATE_CLAIM", "REJECTED", "MALFORMED_CLAIM_ID", str(claim_id) or "<EMPTY>", before, after)
            return False, "MALFORMED_CLAIM_ID"
        if not isinstance(text, str) or not text.strip():
            after = self.state_digest()
            self._record("CREATE_CLAIM", "REJECTED", "MALFORMED_CLAIM_TEXT", claim_id, before, after)
            return False, "MALFORMED_CLAIM_TEXT"
        if claim_id in self.claims:
            after = self.state_digest()
            self._record("CREATE_CLAIM", "IGNORED", "DUPLICATE_CLAIM", claim_id, before, after)
            return False, "DUPLICATE_CLAIM"

        self.claims[claim_id] = Claim(claim_id=claim_id, text=text.strip())
        self._append_history(claim_id, "CLAIM_CREATED")
        after = self.state_digest()
        self._record("CREATE_CLAIM", "ACCEPTED", "CLAIM_CREATED", claim_id, before, after)
        return True, "CLAIM_CREATED"

    def add_evidence(
        self,
        evidence_id: str,
        claim_id: str,
        polarity: str,
        strength: float,
        reliability: float,
        group_id: str,
        description: str,
    ) -> Tuple[bool, str]:
        before = self.state_digest()

        if claim_id not in self.claims:
            after = self.state_digest()
            self._record("ADD_EVIDENCE", "REJECTED", "INVALID_CLAIM_REFERENCE", evidence_id, before, after)
            return False, "INVALID_CLAIM_REFERENCE"
        if evidence_id in self.evidence:
            after = self.state_digest()
            self._record("ADD_EVIDENCE", "IGNORED", "DUPLICATE_EVIDENCE", evidence_id, before, after)
            return False, "DUPLICATE_EVIDENCE"
        if polarity not in VALID_POLARITIES:
            after = self.state_digest()
            self._record("ADD_EVIDENCE", "REJECTED", "INVALID_POLARITY", evidence_id, before, after)
            return False, "INVALID_POLARITY"
        if not isinstance(group_id, str) or not group_id.strip():
            after = self.state_digest()
            self._record("ADD_EVIDENCE", "REJECTED", "MALFORMED_GROUP_ID", evidence_id, before, after)
            return False, "MALFORMED_GROUP_ID"
        if not isinstance(description, str) or not description.strip():
            after = self.state_digest()
            self._record("ADD_EVIDENCE", "REJECTED", "MALFORMED_DESCRIPTION", evidence_id, before, after)
            return False, "MALFORMED_DESCRIPTION"
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (strength, reliability)):
            after = self.state_digest()
            self._record("ADD_EVIDENCE", "REJECTED", "NONFINITE_EVIDENCE_VALUE", evidence_id, before, after)
            return False, "NONFINITE_EVIDENCE_VALUE"
        if not (0.0 <= strength <= 1.0 and 0.0 <= reliability <= 1.0):
            after = self.state_digest()
            self._record("ADD_EVIDENCE", "REJECTED", "EVIDENCE_VALUE_OUT_OF_RANGE", evidence_id, before, after)
            return False, "EVIDENCE_VALUE_OUT_OF_RANGE"

        ev = Evidence(
            evidence_id=evidence_id,
            claim_id=claim_id,
            polarity=polarity,
            strength=float(strength),
            reliability=float(reliability),
            group_id=group_id.strip(),
            description=description.strip(),
        )
        self.evidence[evidence_id] = ev
        self.claims[claim_id].evidence_ids.append(evidence_id)
        self._append_history(claim_id, f"EVIDENCE_ACCEPTED:{evidence_id}")
        self.recompute_claim(claim_id)
        after = self.state_digest()
        self._record("ADD_EVIDENCE", "ACCEPTED", "EVIDENCE_INTEGRATED", evidence_id, before, after)
        return True, "EVIDENCE_INTEGRATED"

    def add_relation(
        self,
        relation_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float,
    ) -> Tuple[bool, str]:
        before = self.state_digest()

        if relation_id in self.relations:
            after = self.state_digest()
            self._record("ADD_RELATION", "IGNORED", "DUPLICATE_RELATION", relation_id, before, after)
            return False, "DUPLICATE_RELATION"
        if relation_type not in VALID_RELATION_TYPES:
            after = self.state_digest()
            self._record("ADD_RELATION", "REJECTED", "INVALID_RELATION_TYPE", relation_id, before, after)
            return False, "INVALID_RELATION_TYPE"
        valid_nodes = set(self.claims) | set(self.evidence)
        if source_id not in valid_nodes or target_id not in valid_nodes:
            after = self.state_digest()
            self._record("ADD_RELATION", "REJECTED", "INVALID_RELATION_REFERENCE", relation_id, before, after)
            return False, "INVALID_RELATION_REFERENCE"
        if not isinstance(strength, (int, float)) or not math.isfinite(strength) or not 0.0 <= strength <= 1.0:
            after = self.state_digest()
            self._record("ADD_RELATION", "REJECTED", "INVALID_RELATION_STRENGTH", relation_id, before, after)
            return False, "INVALID_RELATION_STRENGTH"

        self.relations[relation_id] = Relation(
            relation_id=relation_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=float(strength),
        )
        for node_id in (source_id, target_id):
            if node_id in self.claims:
                self._append_history(node_id, f"RELATION_ACCEPTED:{relation_id}")
        after = self.state_digest()
        self._record("ADD_RELATION", "ACCEPTED", "RELATION_CREATED", relation_id, before, after)
        return True, "RELATION_CREATED"

    def _append_history(self, claim_id: str, event: str) -> None:
        claim = self.claims[claim_id]
        entry = {
            "step": len(claim.history) + 1,
            "event": event,
            "status": claim.status,
        }
        claim.history.append(entry)

    def recompute_claim(self, claim_id: str) -> None:
        claim = self.claims[claim_id]
        attached = [self.evidence[eid] for eid in sorted(claim.evidence_ids)]

        support_weights = [e.weight for e in attached if e.polarity == "SUPPORT"]
        contradiction_weights = [e.weight for e in attached if e.polarity == "CONTRADICTION"]

        # Saturating aggregation: repeated evidence increases weight while remaining bounded.
        support = 1.0 - math.prod(1.0 - w for w in support_weights) if support_weights else 0.0
        contradiction = 1.0 - math.prod(1.0 - w for w in contradiction_weights) if contradiction_weights else 0.0

        groups = {e.group_id for e in attached}
        group_count = len(groups)
        recurrence = len(attached)

        adjusted_support = support * (1.0 - 0.65 * contradiction)
        confidence = self._bounded(
            0.55 * adjusted_support
            + 0.25 * support
            + 0.10 * min(group_count / 4.0, 1.0)
            - 0.20 * contradiction
        )
        persistence = self._bounded(
            0.45 * confidence
            + 0.30 * min(group_count / 4.0, 1.0)
            + 0.25 * min(recurrence / 5.0, 1.0)
        )

        previous_status = claim.status

        if contradiction >= 0.80 and support < 0.35:
            status = STATUS_REJECTED
        elif contradiction >= 0.25 and support >= 0.35:
            status = STATUS_CONTESTED
        elif confidence >= 0.62 and persistence >= 0.60 and group_count >= 2:
            status = STATUS_PERSISTENT
        elif confidence >= 0.38 and support >= 0.45:
            status = STATUS_SUPPORTED
        else:
            status = STATUS_CANDIDATE

        claim.support = round(support, 12)
        claim.contradiction = round(contradiction, 12)
        claim.adjusted_support = round(adjusted_support, 12)
        claim.confidence = round(confidence, 12)
        claim.persistence = round(persistence, 12)
        claim.independent_groups = group_count
        claim.status = status

        if status != previous_status:
            self._append_history(claim_id, f"STATUS_TRANSITION:{previous_status}->{status}")

    def converge(self, max_cycles: int = 25) -> Dict[str, Any]:
        before = self.state_digest()
        previous = None
        cycles = 0

        while cycles < max_cycles:
            cycles += 1
            for claim_id in sorted(self.claims):
                self.recompute_claim(claim_id)
            current = self.state_digest(include_audit=False)
            if current == previous:
                self.last_termination_reason = "STABLE_STATE_REACHED"
                after = self.state_digest()
                self._record(
                    "RECURSIVE_CONVERGENCE",
                    "ACCEPTED",
                    self.last_termination_reason,
                    "SYSTEM",
                    before,
                    after,
                )
                return {"stable": True, "cycles": cycles, "termination_reason": self.last_termination_reason}
            previous = current

        self.last_termination_reason = "MAX_CYCLES_REACHED"
        after = self.state_digest()
        self._record(
            "RECURSIVE_CONVERGENCE",
            "REJECTED",
            self.last_termination_reason,
            "SYSTEM",
            before,
            after,
        )
        return {"stable": False, "cycles": cycles, "termination_reason": self.last_termination_reason}


# --------------------------------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------------------------------

def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def audit_is_complete(engine: MPRDValidationEngine) -> bool:
    if not engine.audit:
        return False
    expected_sequences = list(range(1, len(engine.audit) + 1))
    actual_sequences = [record.sequence for record in engine.audit]
    required_fields_present = all(
        record.operation
        and record.outcome
        and record.reason
        and record.target_id
        and len(record.state_digest_before) == 64
        and len(record.state_digest_after) == 64
        for record in engine.audit
    )
    return actual_sequences == expected_sequences and required_fields_present


def rejected_operation_preserved_state(
    engine: MPRDValidationEngine,
    operation,
    *args,
    **kwargs,
) -> Tuple[bool, str, bool]:
    before = engine.state_digest(include_audit=False)
    accepted, reason = operation(*args, **kwargs)
    after = engine.state_digest(include_audit=False)
    return accepted, reason, before == after


def execute_validation(verbose: bool = False) -> Dict[str, Any]:
    engine = MPRDValidationEngine()
    scenarios: List[Dict[str, Any]] = []

    def record(number: int, name: str, passed: bool, observed: str, expected: str) -> None:
        scenarios.append({
            "number": number,
            "name": name,
            "passed": bool(passed),
            "observed": observed,
            "expected": expected,
        })

    # Scenario 01: Initialize clean state and create candidate claim.
    ok, reason = engine.create_claim(
        "C-001",
        "The integrated MPRD_V1 reasoning workflow is reproducible and auditable.",
    )
    passed = ok and engine.claims["C-001"].status == STATUS_CANDIDATE
    record(1, "Clean initialization and candidate claim", passed, engine.claims["C-001"].status, STATUS_CANDIDATE)

    # Scenario 02: First supporting evidence should produce a supported state.
    ok, reason = engine.add_evidence(
        "E-001", "C-001", "SUPPORT", 0.90, 0.95, "GROUP-A",
        "Independent execution record demonstrates reproducibility.",
    )
    passed = ok and engine.claims["C-001"].status == STATUS_SUPPORTED
    record(2, "Supporting evidence integration", passed, engine.claims["C-001"].status, STATUS_SUPPORTED)

    # Scenario 03: Independent confirmation and relation update.
    ok2, _ = engine.add_evidence(
        "E-002", "C-001", "SUPPORT", 0.88, 0.93, "GROUP-B",
        "Second independent execution produces the same normalized result.",
    )
    ok3, _ = engine.add_relation("R-001", "E-002", "C-001", "SUPPORTS", 0.90)
    claim = engine.claims["C-001"]
    passed = (
        ok2 and ok3
        and claim.status == STATUS_PERSISTENT
        and claim.independent_groups == 2
        and len(engine.relations) == 1
    )
    record(
        3,
        "Independent confirmation, persistence, and relation update",
        passed,
        f"{claim.status}; groups={claim.independent_groups}; relations={len(engine.relations)}",
        "PERSISTENT; groups=2; relations=1",
    )

    # Add further support before contradiction to exercise a fuller evidence path.
    engine.add_evidence(
        "E-003", "C-001", "SUPPORT", 0.82, 0.91, "GROUP-C",
        "Audit reconstruction independently confirms the execution path.",
    )

    # Scenario 04: Controlled contradiction without evidence loss.
    evidence_before = set(engine.evidence)
    ok4, _ = engine.add_evidence(
        "E-004", "C-001", "CONTRADICTION", 0.58, 0.72, "GROUP-D",
        "One observation conflicts with the dominant reproducibility record.",
    )
    evidence_after = set(engine.evidence)
    claim = engine.claims["C-001"]
    passed = (
        ok4
        and claim.status == STATUS_CONTESTED
        and evidence_before.issubset(evidence_after)
        and len(evidence_after) == 4
    )
    record(
        4,
        "Contradiction handling without evidence loss",
        passed,
        f"{claim.status}; preserved={evidence_before.issubset(evidence_after)}",
        "CONTESTED; preserved=True",
    )

    # Scenario 05: Recursive convergence.
    convergence = engine.converge()
    passed = convergence["stable"] and convergence["termination_reason"] == "STABLE_STATE_REACHED"
    record(
        5,
        "Stable recursive convergence",
        passed,
        f"stable={convergence['stable']}; cycles={convergence['cycles']}; reason={convergence['termination_reason']}",
        "stable=True; reason=STABLE_STATE_REACHED",
    )

    # Scenario 06: Duplicate evidence insertion must be safely ignored.
    accepted, reason, preserved = rejected_operation_preserved_state(
        engine,
        engine.add_evidence,
        "E-001", "C-001", "SUPPORT", 0.90, 0.95, "GROUP-A",
        "Duplicate execution record.",
    )
    passed = (not accepted) and reason == "DUPLICATE_EVIDENCE" and preserved
    record(
        6,
        "Duplicate-evidence safeguard",
        passed,
        f"accepted={accepted}; reason={reason}; state_preserved={preserved}",
        "accepted=False; reason=DUPLICATE_EVIDENCE; state_preserved=True",
    )

    # Scenario 07: Invalid references and malformed values must not corrupt the state.
    safeguard_results = []

    safeguard_results.append(rejected_operation_preserved_state(
        engine,
        engine.add_evidence,
        "E-INVALID-CLAIM", "C-999", "SUPPORT", 0.5, 0.5, "GROUP-X", "Invalid claim reference.",
    ))
    safeguard_results.append(rejected_operation_preserved_state(
        engine,
        engine.add_evidence,
        "E-INVALID-POLARITY", "C-001", "UNKNOWN", 0.5, 0.5, "GROUP-X", "Invalid polarity.",
    ))
    safeguard_results.append(rejected_operation_preserved_state(
        engine,
        engine.add_evidence,
        "E-INVALID-RANGE", "C-001", "SUPPORT", 1.5, 0.5, "GROUP-X", "Out-of-range evidence.",
    ))
    safeguard_results.append(rejected_operation_preserved_state(
        engine,
        engine.add_relation,
        "R-INVALID-REF", "E-999", "C-001", "SUPPORTS", 0.5,
    ))
    safeguard_results.append(rejected_operation_preserved_state(
        engine,
        engine.add_relation,
        "R-INVALID-TYPE", "E-001", "C-001", "UNSUPPORTED_TYPE", 0.5,
    ))
    safeguard_results.append(rejected_operation_preserved_state(
        engine,
        engine.create_claim,
        "", "Malformed empty claim identifier.",
    ))

    safeguard_pass = all((not accepted) and preserved for accepted, _, preserved in safeguard_results)
    observed = "; ".join(
        f"{reason}:preserved={preserved}"
        for accepted, reason, preserved in safeguard_results
    )
    record(7, "Invalid-operation containment", safeguard_pass, observed, "All rejected or ignored; valid state preserved")

    # Scenario 08: Complete and chronological audit trail.
    audit_pass = audit_is_complete(engine)
    audit_outcomes = {record.outcome for record in engine.audit}
    audit_reasons = {record.reason for record in engine.audit}
    required_reasons = {
        "CLAIM_CREATED",
        "EVIDENCE_INTEGRATED",
        "RELATION_CREATED",
        "STABLE_STATE_REACHED",
        "DUPLICATE_EVIDENCE",
        "INVALID_CLAIM_REFERENCE",
        "INVALID_RELATION_REFERENCE",
    }
    audit_pass = audit_pass and {"ACCEPTED", "REJECTED", "IGNORED"}.issubset(audit_outcomes)
    audit_pass = audit_pass and required_reasons.issubset(audit_reasons)
    record(
        8,
        "Audit completeness and chronological traceability",
        audit_pass,
        f"records={len(engine.audit)}; outcomes={sorted(audit_outcomes)}",
        "Sequential complete records with ACCEPTED, REJECTED, and IGNORED outcomes",
    )

    # Scenario 09 is verified outside this single execution by the 30-run loop.
    # We record the local normalized output here and replace the scenario result in main().
    record(
        9,
        "Repeated deterministic execution",
        True,
        "Deferred to 30-run verification",
        "1 unique normalized output and 1 unique final state digest",
    )

    # Scenario 10: Execution completeness and final record.
    core_before_closeout = all(item["passed"] for item in scenarios[:8])
    final_claim = engine.claims["C-001"]
    required_entities_preserved = (
        set(final_claim.evidence_ids) == {"E-001", "E-002", "E-003", "E-004"}
        and set(engine.evidence) == {"E-001", "E-002", "E-003", "E-004"}
        and set(engine.relations) == {"R-001"}
    )
    closeout_pass = core_before_closeout and required_entities_preserved and audit_pass
    record(
        10,
        "Execution completeness and Phase 1 validation record",
        closeout_pass,
        f"core_pass={core_before_closeout}; preserved={required_entities_preserved}; audit={audit_pass}",
        "core_pass=True; preserved=True; audit=True",
    )

    normalized_without_audit = engine.normalized_state(include_audit=False)
    normalized_with_audit = engine.normalized_state(include_audit=True)

    result = {
        "test": TEST_NAME,
        "subtitle": TEST_SUBTITLE,
        "algorithm": ALGORITHM_NAME,
        "scenarios": scenarios,
        "scenario_pass_count": sum(1 for item in scenarios if item["passed"]),
        "scenario_total": len(scenarios),
        "scientific_outcome": "PASS" if all(item["passed"] for item in scenarios) else "FAIL",
        "execution_completeness": "COMPLETE",
        "final_claim": {
            "claim_id": final_claim.claim_id,
            "status": final_claim.status,
            "support": round(final_claim.support, 8),
            "contradiction": round(final_claim.contradiction, 8),
            "adjusted_support": round(final_claim.adjusted_support, 8),
            "confidence": round(final_claim.confidence, 8),
            "persistence": round(final_claim.persistence, 8),
            "independent_groups": final_claim.independent_groups,
            "accepted_evidence": len(final_claim.evidence_ids),
            "history_entries": len(final_claim.history),
        },
        "relations": len(engine.relations),
        "audit_records": len(engine.audit),
        "audit_complete": audit_pass,
        "recursive_convergence": convergence,
        "safeguards": {
            "duplicate_evidence": "PASS" if scenarios[5]["passed"] else "FAIL",
            "invalid_operations": "PASS" if scenarios[6]["passed"] else "FAIL",
            "valid_state_preserved": safeguard_pass and scenarios[5]["passed"],
        },
        "normalized_output": normalized_without_audit,
        "state_digest": engine.state_digest(include_audit=False),
        "full_execution_digest": engine._hash(normalized_with_audit),
    }

    if verbose:
        return result
    return result


def print_separator(char: str = "=", width: int = 108) -> None:
    print(char * width)


def main() -> None:
    start = time.perf_counter()

    runs = [execute_validation(verbose=False) for _ in range(REPEAT_RUNS)]
    normalized_digests = [
        hashlib.sha256(
            json.dumps(run["normalized_output"], sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        for run in runs
    ]
    state_digests = [run["state_digest"] for run in runs]
    full_execution_digests = [run["full_execution_digest"] for run in runs]

    unique_normalized = len(set(normalized_digests))
    unique_states = len(set(state_digests))
    unique_full = len(set(full_execution_digests))
    deterministic = unique_normalized == 1 and unique_states == 1 and unique_full == 1

    result = runs[0]
    result["scenarios"][8]["passed"] = deterministic
    result["scenarios"][8]["observed"] = (
        f"{REPEAT_RUNS} runs; normalized={unique_normalized}; "
        f"state={unique_states}; full={unique_full}"
    )
    result["scenario_pass_count"] = sum(1 for item in result["scenarios"] if item["passed"])
    result["scientific_outcome"] = (
        "PASS"
        if result["scenario_pass_count"] == result["scenario_total"] and deterministic
        else "FAIL"
    )
    result["repeatability"] = {
        "runs": REPEAT_RUNS,
        "unique_normalized_outputs": unique_normalized,
        "unique_state_digests": unique_states,
        "unique_full_execution_digests": unique_full,
        "deterministic": deterministic,
    }

    elapsed = time.perf_counter() - start
    result["elapsed_seconds"] = round(elapsed, 6)
    result["generated_utc"] = datetime.now(timezone.utc).isoformat()

    final_claim = result["final_claim"]

    print_separator()
    print(TEST_NAME)
    print(TEST_SUBTITLE)
    print_separator()
    print(f"Algorithm: {ALGORITHM_NAME}")
    print(f"Scientific outcome: {result['scientific_outcome']}")
    print(f"Execution completeness: {result['execution_completeness']}")
    print(f"Core scenarios passed: {result['scenario_pass_count']}/{result['scenario_total']}")
    print(f"Repeatability: {REPEAT_RUNS} runs")
    print(f"Unique normalized outputs: {unique_normalized}")
    print(f"Unique state digests: {unique_states}")
    print(f"Unique full execution digests: {unique_full}")
    print(f"Deterministic: {'YES' if deterministic else 'NO'}")
    print(f"Run digest: {result['state_digest']}")
    print(f"Full execution digest: {result['full_execution_digest']}")
    print(f"Elapsed time: {elapsed:.4f}s")
    print_separator("-")

    for scenario in result["scenarios"]:
        status = "PASS" if scenario["passed"] else "FAIL"
        print(f"Scenario {scenario['number']:02d} | {status} | {scenario['name']}")
        print(f"  Expected: {scenario['expected']}")
        print(f"  Observed: {scenario['observed']}")

    print_separator("-")
    print("FINAL KNOWLEDGE STATE")
    print(f"  Claim status: {final_claim['status']}")
    print(f"  Evidence integrated: {final_claim['accepted_evidence']}")
    print(f"  Independent groups: {final_claim['independent_groups']}")
    print(f"  Relations: {result['relations']}")
    print(f"  Support: {final_claim['support']:.8f}")
    print(f"  Contradiction: {final_claim['contradiction']:.8f}")
    print(f"  Adjusted support: {final_claim['adjusted_support']:.8f}")
    print(f"  Confidence: {final_claim['confidence']:.8f}")
    print(f"  Persistence: {final_claim['persistence']:.8f}")
    print(f"  Claim-history entries: {final_claim['history_entries']}")
    print(f"  Audit records: {result['audit_records']}")
    print(f"  Audit complete: {'YES' if result['audit_complete'] else 'NO'}")
    print(f"  Convergence: {'STABLE' if result['recursive_convergence']['stable'] else 'UNSTABLE'}")
    print(f"  Termination reason: {result['recursive_convergence']['termination_reason']}")
    print_separator("-")
    print("SAFEGUARD SUMMARY")
    print(f"  Duplicate evidence: {result['safeguards']['duplicate_evidence']}")
    print(f"  Invalid operations: {result['safeguards']['invalid_operations']}")
    print(f"  Valid state preserved: {'YES' if result['safeguards']['valid_state_preserved'] else 'NO'}")
    print_separator()

    json_name = "MPRD_V1_Phase_1_Validation_Test_05_Results.json"
    txt_name = "MPRD_V1_Phase_1_Validation_Test_05_Execution_Record.txt"

    with open(json_name, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=False)

    # Save the same console-oriented summary as an archival text record.
    lines = [
        TEST_NAME,
        TEST_SUBTITLE,
        f"Algorithm: {ALGORITHM_NAME}",
        f"Scientific outcome: {result['scientific_outcome']}",
        f"Execution completeness: {result['execution_completeness']}",
        f"Scenarios passed: {result['scenario_pass_count']}/{result['scenario_total']}",
        f"Repeatability: {REPEAT_RUNS} runs",
        f"Deterministic: {'YES' if deterministic else 'NO'}",
        f"State digest: {result['state_digest']}",
        f"Full execution digest: {result['full_execution_digest']}",
        f"Final claim status: {final_claim['status']}",
        f"Support: {final_claim['support']:.8f}",
        f"Contradiction: {final_claim['contradiction']:.8f}",
        f"Adjusted support: {final_claim['adjusted_support']:.8f}",
        f"Confidence: {final_claim['confidence']:.8f}",
        f"Persistence: {final_claim['persistence']:.8f}",
        f"Evidence integrated: {final_claim['accepted_evidence']}",
        f"Independent groups: {final_claim['independent_groups']}",
        f"Relations: {result['relations']}",
        f"Audit records: {result['audit_records']}",
        f"Audit complete: {'YES' if result['audit_complete'] else 'NO'}",
        f"Convergence: {'STABLE' if result['recursive_convergence']['stable'] else 'UNSTABLE'}",
        f"Termination reason: {result['recursive_convergence']['termination_reason']}",
        "",
        "SCENARIOS",
    ]
    for scenario in result["scenarios"]:
        lines.append(
            f"{scenario['number']:02d} | {'PASS' if scenario['passed'] else 'FAIL'} | "
            f"{scenario['name']} | Observed={scenario['observed']}"
        )

    with open(txt_name, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    print(f"Saved: {json_name}")
    print(f"Saved: {txt_name}")

    # Automatic downloads when executed in Google Colab.
    try:
        from google.colab import files  # type: ignore
        print("Starting Colab downloads...")
        files.download(json_name)
        files.download(txt_name)
    except Exception:
        print("Automatic download skipped outside Google Colab.")
        print("The result files are available in the current working directory.")


if __name__ == "__main__":
    main()
