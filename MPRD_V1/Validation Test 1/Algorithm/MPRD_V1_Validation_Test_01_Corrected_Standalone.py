"""
MPRD_V1 Validation Test 01 — Corrected Standalone Google Colab Script
======================================================================

Martin Pitre Framework of Relational Distinction, Persistence,
and Recursive Development

Version: 1.0.1 corrective validation baseline
Author: Martin Pitre
Date: 2026-07-28

Purpose
-------
This single-file script contains the MPRD_V1 core classification engine and
Validation Test 01. It requires only the Python standard library and can be
copied directly into one Google Colab cell.

Corrective changes
------------------
1. A claim supported by only one evidence record from one independence group
   is classified as INSUFFICIENT before the general support rule is evaluated.
2. PERSISTENT status now requires the adjusted support score to satisfy the
   ordinary support threshold as well as the persistence requirements.

These changes prevent:
- one strong observation from becoming SUPPORTED without independent evidence;
- repeated weak observations from becoming PERSISTENT solely through
  recurrence and independence bonuses.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ALGORITHM_NAME = "MPRD_V1 Core Algorithm"
ALGORITHM_VERSION = "1.0.1"
SCHEMA_VERSION = "1.0"
RESULTS_FILE = "MPRD_V1_Validation_Test_01_Corrected_Results.json"


class MPRDError(Exception):
    """Base exception for MPRD processing errors."""


class ValidationError(MPRDError):
    """Raised when input violates the algorithm contract."""


class EvidenceType(str, Enum):
    OBSERVATION = "observation"
    MEASUREMENT = "measurement"
    DOCUMENT = "document"
    TEST_RESULT = "test_result"
    HUMAN_REPORT = "human_report"
    SYSTEM_OUTPUT = "system_output"
    UNKNOWN = "unknown"


class ClaimStatus(str, Enum):
    CANDIDATE = "candidate"
    SUPPORTED = "supported"
    PERSISTENT = "persistent"
    CONTESTED = "contested"
    REJECTED = "rejected"
    INSUFFICIENT = "insufficient"


class RelationType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DUPLICATES = "duplicates"
    EXTENDS = "extends"
    DEPENDS_ON = "depends_on"
    CONTEXTUALIZES = "contextualizes"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    claim: str
    source_id: str
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    quality: float = 0.5
    reliability: float = 0.5
    independence_group: str = ""
    timestamp_utc: str = ""
    provenance: str = ""
    notes: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validated(self) -> "EvidenceRecord":
        evidence_id = self.evidence_id.strip()
        claim = self.claim.strip()
        source_id = self.source_id.strip()

        if not evidence_id:
            raise ValidationError("evidence_id must not be empty.")
        if not claim:
            raise ValidationError("claim must not be empty.")
        if not source_id:
            raise ValidationError("source_id must not be empty.")

        for name, value in (("quality", self.quality), ("reliability", self.reliability)):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValidationError(f"{name} must be numeric.")
            if not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
                raise ValidationError(f"{name} must be between 0.0 and 1.0.")

        timestamp = self.timestamp_utc.strip() or utc_now()
        validate_iso_utc(timestamp)
        independence_group = self.independence_group.strip() or f"source:{source_id}"

        return EvidenceRecord(
            evidence_id=evidence_id,
            claim=claim,
            source_id=source_id,
            evidence_type=EvidenceType(self.evidence_type),
            quality=float(self.quality),
            reliability=float(self.reliability),
            independence_group=independence_group,
            timestamp_utc=timestamp,
            provenance=self.provenance.strip(),
            notes=self.notes.strip(),
            metadata=canonicalize_json_value(dict(self.metadata)),
        )


@dataclass(frozen=True)
class Relation:
    relation_id: str
    source_evidence_id: str
    target_evidence_id: str
    relation_type: RelationType
    strength: float
    rationale: str = ""

    def validated(self) -> "Relation":
        relation_id = self.relation_id.strip()
        source_id = self.source_evidence_id.strip()
        target_id = self.target_evidence_id.strip()

        if not relation_id:
            raise ValidationError("relation_id must not be empty.")
        if not source_id:
            raise ValidationError("source_evidence_id must not be empty.")
        if not target_id:
            raise ValidationError("target_evidence_id must not be empty.")
        if source_id == target_id:
            raise ValidationError("A relation cannot target itself.")
        if not isinstance(self.strength, (int, float)) or isinstance(self.strength, bool):
            raise ValidationError("relation strength must be numeric.")
        if not math.isfinite(float(self.strength)) or not 0.0 <= float(self.strength) <= 1.0:
            raise ValidationError("relation strength must be between 0.0 and 1.0.")

        return Relation(
            relation_id=relation_id,
            source_evidence_id=source_id,
            target_evidence_id=target_id,
            relation_type=RelationType(self.relation_type),
            strength=float(self.strength),
            rationale=self.rationale.strip(),
        )


@dataclass(frozen=True)
class MPRDConfig:
    support_threshold: float = 0.60
    persistence_threshold: float = 0.75
    rejection_threshold: float = 0.25
    contradiction_penalty: float = 0.65
    independence_weight: float = 0.20
    recurrence_weight: float = 0.15
    relational_weight: float = 0.20
    evidence_weight: float = 0.45
    minimum_independent_groups_for_persistence: int = 2
    minimum_records_for_persistence: int = 2

    def validated(self) -> "MPRDConfig":
        values = (
            self.support_threshold,
            self.persistence_threshold,
            self.rejection_threshold,
            self.contradiction_penalty,
            self.independence_weight,
            self.recurrence_weight,
            self.relational_weight,
            self.evidence_weight,
        )
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in values):
            raise ValidationError("Configuration values must be numeric.")
        if any(not math.isfinite(float(v)) or not 0.0 <= float(v) <= 1.0 for v in values):
            raise ValidationError("Configuration values must be between 0.0 and 1.0.")

        total_weight = (
            self.independence_weight
            + self.recurrence_weight
            + self.relational_weight
            + self.evidence_weight
        )
        if not math.isclose(total_weight, 1.0, abs_tol=1e-9):
            raise ValidationError("Scoring weights must total 1.0.")
        if self.rejection_threshold >= self.support_threshold:
            raise ValidationError("rejection_threshold must be lower than support_threshold.")
        if self.support_threshold > self.persistence_threshold:
            raise ValidationError("support_threshold must not exceed persistence_threshold.")
        if self.minimum_independent_groups_for_persistence < 1:
            raise ValidationError("minimum independent groups must be at least 1.")
        if self.minimum_records_for_persistence < 1:
            raise ValidationError("minimum records must be at least 1.")
        return self


@dataclass
class ClaimState:
    claim_id: str
    canonical_claim: str
    evidence_ids: List[str]
    support_score: float
    contradiction_score: float
    confidence: float
    persistence_score: float
    internal_relevance: float
    status: ClaimStatus
    independent_groups: int
    recurrence_count: int
    supporting_relations: int
    contradicting_relations: int
    rationale: List[str]


@dataclass(frozen=True)
class ProcessingResult:
    recursion_cycle: int
    updated_claim_ids: Tuple[str, ...]
    state_digest: str


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: int
    title: str
    expected: str
    observed: str
    passed: bool
    details: str
    deterministic: Optional[bool] = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_iso_utc(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValidationError("Timestamp must include timezone information.")
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValidationError("Timestamp must be expressed in UTC.")


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def normalize_claim(claim: str) -> str:
    return " ".join(claim.casefold().strip().split())


def stable_id(prefix: str, value: str, length: int = 16) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:length]}"


def canonicalize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError("Metadata cannot contain NaN or infinity.")
        return value
    if isinstance(value, Mapping):
        return {
            str(key): canonicalize_json_value(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, (list, tuple)):
        return [canonicalize_json_value(item) for item in value]
    raise ValidationError(f"Unsupported metadata type: {type(value).__name__}.")


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def find_duplicates(values: Sequence[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


class MPRDCoreAlgorithm:
    def __init__(self, config: Optional[MPRDConfig] = None) -> None:
        self.config = (config or MPRDConfig()).validated()
        self.recursion_cycle = 0
        self.evidence: Dict[str, EvidenceRecord] = {}
        self.relations: Dict[str, Relation] = {}
        self.claims: Dict[str, ClaimState] = {}

    def process(
        self,
        evidence_records: Iterable[EvidenceRecord],
        relations: Iterable[Relation] = (),
    ) -> ProcessingResult:
        validated_evidence = [item.validated() for item in evidence_records]
        validated_relations = [item.validated() for item in relations]

        evidence_ids = [item.evidence_id for item in validated_evidence]
        relation_ids = [item.relation_id for item in validated_relations]
        duplicate_evidence = find_duplicates(evidence_ids)
        duplicate_relations = find_duplicates(relation_ids)
        if duplicate_evidence:
            raise ValidationError(f"Duplicate evidence IDs in batch: {sorted(duplicate_evidence)}")
        if duplicate_relations:
            raise ValidationError(f"Duplicate relation IDs in batch: {sorted(duplicate_relations)}")

        available_ids = set(self.evidence) | set(evidence_ids)
        for relation in validated_relations:
            missing = {
                evidence_id
                for evidence_id in (relation.source_evidence_id, relation.target_evidence_id)
                if evidence_id not in available_ids
            }
            if missing:
                raise ValidationError(
                    f"Relation {relation.relation_id!r} references unknown evidence IDs: {sorted(missing)}"
                )

        for item in validated_evidence:
            existing = self.evidence.get(item.evidence_id)
            if existing is not None and existing != item:
                raise ValidationError(
                    f"Evidence ID {item.evidence_id!r} already exists with different content."
                )
            self.evidence[item.evidence_id] = item

        for item in validated_relations:
            existing = self.relations.get(item.relation_id)
            if existing is not None and existing != item:
                raise ValidationError(
                    f"Relation ID {item.relation_id!r} already exists with different content."
                )
            self.relations[item.relation_id] = item

        self.recursion_cycle += 1
        affected_claim_ids = {
            stable_id("claim", normalize_claim(item.claim)) for item in validated_evidence
        }
        for relation in validated_relations:
            for evidence_id in (relation.source_evidence_id, relation.target_evidence_id):
                affected_claim_ids.add(
                    stable_id("claim", normalize_claim(self.evidence[evidence_id].claim))
                )

        for claim_id in sorted(affected_claim_ids):
            self._recalculate_claim(claim_id)

        return ProcessingResult(
            recursion_cycle=self.recursion_cycle,
            updated_claim_ids=tuple(sorted(affected_claim_ids)),
            state_digest=self.state_digest(),
        )

    def _recalculate_claim(self, claim_id: str) -> None:
        matching = [
            item
            for item in self.evidence.values()
            if stable_id("claim", normalize_claim(item.claim)) == claim_id
        ]
        matching.sort(key=lambda item: item.evidence_id)
        if not matching:
            return

        evidence_ids = [item.evidence_id for item in matching]
        evidence_id_set = set(evidence_ids)
        relevant_relations = [
            relation
            for relation in self.relations.values()
            if relation.source_evidence_id in evidence_id_set
            or relation.target_evidence_id in evidence_id_set
        ]

        supporting = [
            relation
            for relation in relevant_relations
            if relation.relation_type
            in {
                RelationType.SUPPORTS,
                RelationType.DUPLICATES,
                RelationType.EXTENDS,
                RelationType.CONTEXTUALIZES,
            }
        ]
        contradicting = [
            relation
            for relation in relevant_relations
            if relation.relation_type is RelationType.CONTRADICTS
        ]

        evidence_score = sum(item.quality * item.reliability for item in matching) / len(matching)
        independent_groups = len({item.independence_group for item in matching})
        recurrence_count = len(matching)

        independence_score = clamp(
            independent_groups / max(1, self.config.minimum_independent_groups_for_persistence)
        )
        recurrence_score = clamp(
            recurrence_count / max(1, self.config.minimum_records_for_persistence)
        )

        positive_strength = sum(item.strength for item in supporting)
        negative_strength = sum(item.strength for item in contradicting)
        denominator = positive_strength + negative_strength
        relational_score = 0.5 if denominator == 0 else positive_strength / denominator

        raw_support = (
            self.config.evidence_weight * evidence_score
            + self.config.independence_weight * independence_score
            + self.config.recurrence_weight * recurrence_score
            + self.config.relational_weight * relational_score
        )

        contradiction_score = clamp(
            negative_strength / max(1.0, float(len(contradicting)))
        )
        adjusted_support = clamp(
            raw_support * (1.0 - self.config.contradiction_penalty * contradiction_score)
        )

        completeness = clamp(0.5 * independence_score + 0.5 * recurrence_score)
        consistency = 1.0 - contradiction_score
        confidence = clamp(
            0.55 * adjusted_support + 0.25 * completeness + 0.20 * consistency
        )
        persistence_score = clamp(
            0.50 * adjusted_support + 0.30 * independence_score + 0.20 * recurrence_score
        )
        relation_density = clamp(
            len(relevant_relations) / max(1.0, float(len(self.relations)))
        )
        internal_relevance = clamp(0.60 * persistence_score + 0.40 * relation_density)

        status, rationale = self._determine_status(
            adjusted_support=adjusted_support,
            persistence_score=persistence_score,
            contradiction_score=contradiction_score,
            independent_groups=independent_groups,
            recurrence_count=recurrence_count,
        )

        canonical_claim = min(
            (item.claim for item in matching), key=lambda text: (len(text), text.casefold())
        )
        self.claims[claim_id] = ClaimState(
            claim_id=claim_id,
            canonical_claim=canonical_claim,
            evidence_ids=evidence_ids,
            support_score=round(adjusted_support, 6),
            contradiction_score=round(contradiction_score, 6),
            confidence=round(confidence, 6),
            persistence_score=round(persistence_score, 6),
            internal_relevance=round(internal_relevance, 6),
            status=status,
            independent_groups=independent_groups,
            recurrence_count=recurrence_count,
            supporting_relations=len(supporting),
            contradicting_relations=len(contradicting),
            rationale=rationale,
        )

    def _determine_status(
        self,
        *,
        adjusted_support: float,
        persistence_score: float,
        contradiction_score: float,
        independent_groups: int,
        recurrence_count: int,
    ) -> Tuple[ClaimStatus, List[str]]:
        """Corrected classification method used by Validation Test 01."""
        rationale: List[str] = []

        if (
            contradiction_score >= 0.50
            and adjusted_support >= self.config.rejection_threshold
        ):
            rationale.append("Material contradictory evidence remains unresolved.")
            return ClaimStatus.CONTESTED, rationale

        if adjusted_support < self.config.rejection_threshold:
            rationale.append("Adjusted support is below the rejection threshold.")
            return ClaimStatus.REJECTED, rationale

        # CORRECTION 1:
        # A single record from one independence group cannot become SUPPORTED,
        # regardless of its individual quality or reliability.
        if recurrence_count == 1 and independent_groups == 1:
            rationale.append(
                "Only one evidence record from one independence group is available. "
                "Independent confirmation is required."
            )
            return ClaimStatus.INSUFFICIENT, rationale

        # CORRECTION 2:
        # Persistence requires ordinary support adequacy in addition to
        # persistence score, independent confirmation, and recurrence.
        persistence_requirements_met = (
            adjusted_support >= self.config.support_threshold
            and persistence_score >= self.config.persistence_threshold
            and independent_groups
            >= self.config.minimum_independent_groups_for_persistence
            and recurrence_count >= self.config.minimum_records_for_persistence
        )

        if persistence_requirements_met:
            rationale.extend(
                [
                    "Support threshold satisfied.",
                    "Persistence threshold satisfied.",
                    "Minimum independent confirmation requirement satisfied.",
                    "Minimum recurrence requirement satisfied.",
                ]
            )
            return ClaimStatus.PERSISTENT, rationale

        if adjusted_support >= self.config.support_threshold:
            rationale.append(
                "Support threshold satisfied, but full persistence criteria are not yet satisfied."
            )
            return ClaimStatus.SUPPORTED, rationale

        rationale.append("Claim remains a candidate pending stronger evidence.")
        return ClaimStatus.CANDIDATE, rationale

    def state_digest(self) -> str:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "algorithm_name": ALGORITHM_NAME,
            "algorithm_version": ALGORITHM_VERSION,
            "recursion_cycle": self.recursion_cycle,
            "evidence": {
                key: {
                    "evidence_id": value.evidence_id,
                    "claim": value.claim,
                    "source_id": value.source_id,
                    "evidence_type": value.evidence_type.value,
                    "quality": value.quality,
                    "reliability": value.reliability,
                    "independence_group": value.independence_group,
                    "provenance": value.provenance,
                    "notes": value.notes,
                    "metadata": canonicalize_json_value(dict(value.metadata)),
                }
                for key, value in sorted(self.evidence.items())
            },
            "relations": {
                key: {
                    "relation_id": value.relation_id,
                    "source_evidence_id": value.source_evidence_id,
                    "target_evidence_id": value.target_evidence_id,
                    "relation_type": value.relation_type.value,
                    "strength": value.strength,
                    "rationale": value.rationale,
                }
                for key, value in sorted(self.relations.items())
            },
            "claims": {
                key: {
                    "claim_id": value.claim_id,
                    "canonical_claim": value.canonical_claim,
                    "evidence_ids": value.evidence_ids,
                    "support_score": value.support_score,
                    "contradiction_score": value.contradiction_score,
                    "confidence": value.confidence,
                    "persistence_score": value.persistence_score,
                    "internal_relevance": value.internal_relevance,
                    "status": value.status.value,
                    "independent_groups": value.independent_groups,
                    "recurrence_count": value.recurrence_count,
                    "supporting_relations": value.supporting_relations,
                    "contradicting_relations": value.contradicting_relations,
                    "rationale": value.rationale,
                }
                for key, value in sorted(self.claims.items())
            },
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def make_engine() -> MPRDCoreAlgorithm:
    return MPRDCoreAlgorithm()


def run_valid_scenario(
    scenario_id: int,
    title: str,
    records: List[EvidenceRecord],
    relations: List[Relation],
    expected_statuses: set[ClaimStatus],
) -> ScenarioResult:
    engine_a = make_engine()
    result_a = engine_a.process(records, relations)

    if len(result_a.updated_claim_ids) != 1:
        return ScenarioResult(
            scenario_id,
            title,
            "/".join(sorted(s.value.upper() for s in expected_statuses)),
            f"{len(result_a.updated_claim_ids)} updated claims",
            False,
            "Expected exactly one updated claim.",
            False,
        )

    claim_a = engine_a.claims[result_a.updated_claim_ids[0]]
    engine_b = make_engine()
    result_b = engine_b.process(records, relations)
    claim_b = engine_b.claims[result_b.updated_claim_ids[0]]

    deterministic = (
        claim_a.status == claim_b.status
        and claim_a.support_score == claim_b.support_score
        and claim_a.persistence_score == claim_b.persistence_score
        and claim_a.confidence == claim_b.confidence
        and result_a.state_digest == result_b.state_digest
    )
    passed = claim_a.status in expected_statuses and deterministic

    return ScenarioResult(
        scenario_id=scenario_id,
        title=title,
        expected="/".join(sorted(s.value.upper() for s in expected_statuses)),
        observed=claim_a.status.value.upper(),
        passed=passed,
        details=(
            f"Status={claim_a.status.value.upper()} | "
            f"Support={claim_a.support_score:.6f} | "
            f"Persistence={claim_a.persistence_score:.6f} | "
            f"Confidence={claim_a.confidence:.6f} | "
            f"Digest={result_a.state_digest}"
        ),
        deterministic=deterministic,
    )


def run_error_scenario(
    scenario_id: int,
    title: str,
    action: Callable[[], None],
) -> ScenarioResult:
    try:
        action()
    except ValidationError as exc:
        return ScenarioResult(
            scenario_id, title, "ValidationError", "ValidationError", True, str(exc)
        )
    except Exception as exc:
        return ScenarioResult(
            scenario_id,
            title,
            "ValidationError",
            type(exc).__name__,
            False,
            f"Unexpected exception: {exc}",
        )
    return ScenarioResult(
        scenario_id,
        title,
        "ValidationError",
        "NO ERROR",
        False,
        "Invalid input was accepted.",
    )


def scenario_01() -> ScenarioResult:
    return run_valid_scenario(
        1,
        "One low-quality observation",
        [
            EvidenceRecord(
                evidence_id="S01_E001",
                claim="The controlled result is stable.",
                source_id="single_low_quality_source",
                quality=0.20,
                reliability=0.20,
                independence_group="group_01",
                timestamp_utc="2026-07-28T13:00:00Z",
            )
        ],
        [],
        {ClaimStatus.INSUFFICIENT},
    )


def scenario_02() -> ScenarioResult:
    return run_valid_scenario(
        2,
        "One high-quality observation",
        [
            EvidenceRecord(
                evidence_id="S02_E001",
                claim="The controlled result is stable.",
                source_id="single_high_quality_source",
                evidence_type=EvidenceType.TEST_RESULT,
                quality=0.95,
                reliability=0.95,
                independence_group="group_01",
                timestamp_utc="2026-07-28T13:05:00Z",
            )
        ],
        [],
        {ClaimStatus.INSUFFICIENT},
    )


def scenario_03() -> ScenarioResult:
    records = [
        EvidenceRecord(
            evidence_id="S03_E001",
            claim="The controlled result is reproducible.",
            source_id="run_01",
            evidence_type=EvidenceType.TEST_RESULT,
            quality=0.95,
            reliability=0.95,
            independence_group="group_01",
            timestamp_utc="2026-07-28T13:10:00Z",
        ),
        EvidenceRecord(
            evidence_id="S03_E002",
            claim="The controlled result is reproducible.",
            source_id="run_02",
            evidence_type=EvidenceType.TEST_RESULT,
            quality=0.95,
            reliability=0.95,
            independence_group="group_02",
            timestamp_utc="2026-07-28T13:11:00Z",
        ),
    ]
    relations = [
        Relation(
            relation_id="S03_R001",
            source_evidence_id="S03_E002",
            target_evidence_id="S03_E001",
            relation_type=RelationType.SUPPORTS,
            strength=0.95,
            rationale="Independent repeat supports the same claim.",
        )
    ]
    return run_valid_scenario(
        3,
        "Two independent strong observations",
        records,
        relations,
        {ClaimStatus.PERSISTENT},
    )


def scenario_04() -> ScenarioResult:
    records = [
        EvidenceRecord(
            evidence_id="S04_E001",
            claim="The weak signal is meaningful.",
            source_id="weak_run_01",
            quality=0.40,
            reliability=0.40,
            independence_group="group_01",
            timestamp_utc="2026-07-28T13:15:00Z",
        ),
        EvidenceRecord(
            evidence_id="S04_E002",
            claim="The weak signal is meaningful.",
            source_id="weak_run_02",
            quality=0.40,
            reliability=0.40,
            independence_group="group_02",
            timestamp_utc="2026-07-28T13:16:00Z",
        ),
    ]
    return run_valid_scenario(
        4,
        "Two weak observations",
        records,
        [],
        {ClaimStatus.CANDIDATE},
    )


def scenario_05() -> ScenarioResult:
    records = [
        EvidenceRecord(
            evidence_id="S05_E001",
            claim="The result remains valid under review.",
            source_id="supporting_run",
            evidence_type=EvidenceType.TEST_RESULT,
            quality=0.95,
            reliability=0.95,
            independence_group="support_group",
            timestamp_utc="2026-07-28T13:20:00Z",
        ),
        EvidenceRecord(
            evidence_id="S05_E002",
            claim="The result remains valid under review.",
            source_id="contradicting_run",
            evidence_type=EvidenceType.TEST_RESULT,
            quality=0.90,
            reliability=0.90,
            independence_group="contradiction_group",
            timestamp_utc="2026-07-28T13:21:00Z",
        ),
    ]
    relations = [
        Relation(
            relation_id="S05_R001",
            source_evidence_id="S05_E002",
            target_evidence_id="S05_E001",
            relation_type=RelationType.CONTRADICTS,
            strength=0.90,
            rationale="Independent evidence materially contradicts the claim.",
        )
    ]
    return run_valid_scenario(
        5,
        "Strong evidence with contradiction",
        records,
        relations,
        {ClaimStatus.CONTESTED},
    )


def scenario_06() -> ScenarioResult:
    records = [
        EvidenceRecord(
            evidence_id=f"S06_E{i:03d}",
            claim="The multi-run result is stable.",
            source_id=f"run_{i}",
            evidence_type=EvidenceType.TEST_RESULT,
            quality=0.90,
            reliability=0.90,
            independence_group=f"group_{i}",
            timestamp_utc=f"2026-07-28T13:{25+i:02d}:00Z",
        )
        for i in range(1, 5)
    ]
    relations = [
        Relation(
            relation_id=f"S06_R{i:03d}",
            source_evidence_id=f"S06_E{i+1:03d}",
            target_evidence_id="S06_E001",
            relation_type=RelationType.SUPPORTS,
            strength=0.90,
            rationale="Independent confirmation supports the same claim.",
        )
        for i in range(1, 4)
    ]
    return run_valid_scenario(
        6,
        "Multiple independent confirmations",
        records,
        relations,
        {ClaimStatus.PERSISTENT},
    )


def scenario_07() -> ScenarioResult:
    def action() -> None:
        make_engine().process(
            [
                EvidenceRecord(
                    evidence_id="DUPLICATE_ID",
                    claim="Duplicate IDs must be rejected.",
                    source_id="source_01",
                    quality=0.80,
                    reliability=0.80,
                    timestamp_utc="2026-07-28T13:35:00Z",
                ),
                EvidenceRecord(
                    evidence_id="DUPLICATE_ID",
                    claim="Duplicate IDs must be rejected.",
                    source_id="source_02",
                    quality=0.80,
                    reliability=0.80,
                    timestamp_utc="2026-07-28T13:36:00Z",
                ),
            ]
        )

    return run_error_scenario(7, "Duplicate evidence IDs", action)


def scenario_08() -> ScenarioResult:
    def action() -> None:
        make_engine().process(
            [
                EvidenceRecord(
                    evidence_id="S08_E001",
                    claim="Invalid quality must be rejected.",
                    source_id="source_01",
                    quality=1.10,
                    reliability=0.80,
                    timestamp_utc="2026-07-28T13:40:00Z",
                )
            ]
        )

    return run_error_scenario(8, "Invalid quality greater than 1", action)


def scenario_09() -> ScenarioResult:
    def action() -> None:
        make_engine().process(
            [
                EvidenceRecord(
                    evidence_id="S09_E001",
                    claim="Invalid reliability must be rejected.",
                    source_id="source_01",
                    quality=0.80,
                    reliability=-0.10,
                    timestamp_utc="2026-07-28T13:45:00Z",
                )
            ]
        )

    return run_error_scenario(9, "Invalid reliability below 0", action)


def scenario_10() -> ScenarioResult:
    def action() -> None:
        make_engine().process(
            [
                EvidenceRecord(
                    evidence_id="",
                    claim="Missing evidence IDs must be rejected.",
                    source_id="source_01",
                    quality=0.80,
                    reliability=0.80,
                    timestamp_utc="2026-07-28T13:50:00Z",
                )
            ]
        )

    return run_error_scenario(10, "Missing evidence ID", action)


def print_result(result: ScenarioResult) -> None:
    print("-" * 88)
    print(f"SCENARIO {result.scenario_id:02d}: {result.title}")
    print(f"Expected: {result.expected}")
    print(f"Observed: {result.observed}")
    if result.deterministic is not None:
        print(f"Deterministic repeat: {'PASS' if result.deterministic else 'FAIL'}")
    print(f"Result: {'PASS' if result.passed else 'FAIL'}")
    print(f"Details: {result.details}")


def validation_test_01_main() -> int:
    print("=" * 88)
    print("MPRD_V1 VALIDATION TEST 01 — CORRECTED RERUN")
    print("Core State Classification Validation")
    print(f"Algorithm version: {ALGORITHM_VERSION}")
    print("=" * 88)

    scenario_functions = [
        scenario_01,
        scenario_02,
        scenario_03,
        scenario_04,
        scenario_05,
        scenario_06,
        scenario_07,
        scenario_08,
        scenario_09,
        scenario_10,
    ]

    results: List[ScenarioResult] = []
    for function in scenario_functions:
        try:
            result = function()
        except Exception as exc:
            result = ScenarioResult(
                scenario_id=len(results) + 1,
                title=function.__name__,
                expected="Controlled expected result",
                observed=type(exc).__name__,
                passed=False,
                details=f"Unhandled exception: {exc}",
            )
        results.append(result)
        print_result(result)

    passed_count = sum(result.passed for result in results)
    failed_count = len(results) - passed_count
    overall_pass = failed_count == 0

    print("=" * 88)
    print("VALIDATION SUMMARY")
    print("=" * 88)
    print(f"Scenarios executed: {len(results)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"OVERALL RESULT: {'PASS' if overall_pass else 'FAIL'}")
    print("=" * 88)

    payload = {
        "test": "MPRD_V1 Validation Test 01 — Corrected Rerun",
        "title": "Core State Classification Validation",
        "algorithm_version": ALGORITHM_VERSION,
        "corrective_changes": [
            "Single-record single-group claims are evaluated as INSUFFICIENT before support classification.",
            "PERSISTENT classification requires adjusted support to meet the support threshold.",
        ],
        "scenarios_executed": len(results),
        "passed": passed_count,
        "failed": failed_count,
        "overall_result": "PASS" if overall_pass else "FAIL",
        "results": [
            {
                "scenario_id": item.scenario_id,
                "title": item.title,
                "expected": item.expected,
                "observed": item.observed,
                "passed": item.passed,
                "details": item.details,
                "deterministic": item.deterministic,
            }
            for item in results
        ],
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(f"Results saved to: {RESULTS_FILE}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    validation_exit_code = validation_test_01_main()
    running_in_notebook = "google.colab" in sys.modules or "ipykernel" in sys.modules
    if not running_in_notebook:
        raise SystemExit(validation_exit_code)
