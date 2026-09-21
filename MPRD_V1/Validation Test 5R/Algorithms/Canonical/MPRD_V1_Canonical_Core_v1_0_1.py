"""Canonical MPRD_V1 Core Algorithm v1.0.1.

Martin Pitre Framework of Relational Distinction, Persistence,
and Recursive Development

This module is the single classification authority for the MPRD_V1 Phase 1
reconciliation baseline.  It contains no validation-test scenarios, output
generation, plotting, Colab downloads, or Test 05R acceptance logic.

Canonical lineage
-----------------
* The scoring model is the common v1.0.1 implementation used by Phase 1
  Validation Tests 03 and 04.
* The classification order preserves the corrective invariants established by
  corrected Validation Test 01:
    1. one supporting record from one group is INSUFFICIENT;
    2. PERSISTENT also requires the ordinary support threshold.
* Test 05R and later harnesses must import this module rather than reproduce
  its formulas.

Only the Python standard library is required.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Tuple


ALGORITHM_NAME = "MPRD_V1 Core Algorithm"
ALGORITHM_VERSION = "1.0.1"
CANONICAL_MODULE_NAME = "MPRD_V1_Canonical_Core_v1_0_1.py"
SCHEMA_VERSION = "1.0"
CLASSIFICATION_ORDER = (
    "CANDIDATE_NO_EVIDENCE",
    "INSUFFICIENT_SINGLE_SOURCE",
    "REJECTED_STRONG_CONTRADICTION",
    "CONTESTED_MATERIAL_CONTRADICTION",
    "PERSISTENT",
    "SUPPORTED",
    "REJECTED_LOW_ADJUSTED_SUPPORT",
    "CANDIDATE_INCOMPLETE_SUPPORT",
)


class MPRDError(Exception):
    """Base exception for canonical MPRD processing errors."""


class ValidationError(MPRDError):
    """Raised before malformed input can affect a canonical state."""


class ConfigurationMismatch(MPRDError):
    """Raised when a harness requests a different frozen configuration."""


class EvidencePolarity(str, Enum):
    SUPPORT = "support"
    CONTRADICTION = "contradiction"


class RelationType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class ClaimStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    SUPPORTED = "SUPPORTED"
    PERSISTENT = "PERSISTENT"
    CONTESTED = "CONTESTED"
    REJECTED = "REJECTED"
    INSUFFICIENT = "INSUFFICIENT"


def _require_identifier(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string.")
    return value.strip()


def _require_unit_interval(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be numeric.")
    converted = float(value)
    if not math.isfinite(converted) or not 0.0 <= converted <= 1.0:
        raise ValidationError(f"{name} must be between 0.0 and 1.0.")
    return converted


def canonical_json(value: Any) -> str:
    """Serialize a JSON-compatible value deterministically."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def stable_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class EvidenceRecord:
    """One evidence item associated with one explicit claim."""

    evidence_id: str
    claim_id: str
    source_id: str
    independence_group: str
    polarity: EvidencePolarity
    strength: float
    reliability: float
    cycle: int
    description: str = ""
    provenance: str = ""

    def validated(self) -> "EvidenceRecord":
        if isinstance(self.cycle, bool) or not isinstance(self.cycle, int) or self.cycle < 1:
            raise ValidationError("cycle must be an integer of at least 1.")
        try:
            polarity = EvidencePolarity(self.polarity)
        except (TypeError, ValueError) as exc:
            raise ValidationError("polarity must be support or contradiction.") from exc
        return EvidenceRecord(
            evidence_id=_require_identifier("evidence_id", self.evidence_id),
            claim_id=_require_identifier("claim_id", self.claim_id),
            source_id=_require_identifier("source_id", self.source_id),
            independence_group=_require_identifier(
                "independence_group", self.independence_group
            ),
            polarity=polarity,
            strength=_require_unit_interval("strength", self.strength),
            reliability=_require_unit_interval("reliability", self.reliability),
            cycle=self.cycle,
            description=str(self.description).strip(),
            provenance=str(self.provenance).strip(),
        )


@dataclass(frozen=True)
class RelationRecord:
    """A traceable evidence-to-claim relationship.

    Relations are validated and preserved in the canonical state.  Phase 1
    v1.0.1 claim scoring is evidence-polarity based, so relation records do not
    add a second score on top of the evidence that they describe.
    """

    relation_id: str
    source_evidence_id: str
    target_claim_id: str
    relation_type: RelationType
    strength: float
    rationale: str = ""

    def validated(self) -> "RelationRecord":
        try:
            relation_type = RelationType(self.relation_type)
        except (TypeError, ValueError) as exc:
            raise ValidationError("relation_type must be supports or contradicts.") from exc
        return RelationRecord(
            relation_id=_require_identifier("relation_id", self.relation_id),
            source_evidence_id=_require_identifier(
                "source_evidence_id", self.source_evidence_id
            ),
            target_claim_id=_require_identifier("target_claim_id", self.target_claim_id),
            relation_type=relation_type,
            strength=_require_unit_interval("relation strength", self.strength),
            rationale=str(self.rationale).strip(),
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
        unit_fields = (
            "support_threshold",
            "persistence_threshold",
            "rejection_threshold",
            "contradiction_contested_threshold",
            "contradiction_penalty",
            "evidence_weight",
            "independence_weight",
            "recurrence_weight",
            "relational_weight",
        )
        for name in unit_fields:
            _require_unit_interval(name, getattr(self, name))
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
        for name in (
            "minimum_independent_groups_for_support",
            "minimum_independent_groups_for_persistence",
            "minimum_records_for_persistence",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError(f"{name} must be a positive integer.")
        return self


FROZEN_CONFIG = MPRDConfig().validated()
FROZEN_CONFIG_DIGEST = stable_digest(asdict(FROZEN_CONFIG))


@dataclass(frozen=True)
class ClaimState:
    claim_id: str
    assessment_cycle: int
    evidence_count: int
    support_count: int
    contradiction_count: int
    independent_groups: int
    recurrence_count: int
    support_score: float
    contradiction_score: float
    adjusted_support: float
    confidence: float
    persistence: float
    status: ClaimStatus
    evidence_ids: Tuple[str, ...]
    relation_ids: Tuple[str, ...]
    rationale: Tuple[str, ...]
    substantive_digest: str

    def canonical_payload(self) -> Mapping[str, Any]:
        """Return the complete deterministic substantive state."""
        payload = asdict(self)
        payload["status"] = self.status.value
        payload.pop("substantive_digest")
        return payload


def evidence_strength(record: EvidenceRecord) -> float:
    """Canonical geometric combination used in Tests 03 and 04."""
    validated = record.validated()
    return math.sqrt(validated.strength * validated.reliability)


def validate_packet(
    claim_id: str,
    evidence: Sequence[EvidenceRecord],
    relations: Sequence[RelationRecord] = (),
) -> Tuple[Tuple[EvidenceRecord, ...], Tuple[RelationRecord, ...]]:
    claim_id = _require_identifier("claim_id", claim_id)
    validated_evidence = tuple(item.validated() for item in evidence)
    evidence_ids = [item.evidence_id for item in validated_evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValidationError("Duplicate evidence_id detected.")
    if any(item.claim_id != claim_id for item in validated_evidence):
        raise ValidationError("Every evidence record must reference the requested claim_id.")

    validated_relations = tuple(item.validated() for item in relations)
    relation_ids = [item.relation_id for item in validated_relations]
    if len(relation_ids) != len(set(relation_ids)):
        raise ValidationError("Duplicate relation_id detected.")
    known_evidence = set(evidence_ids)
    for relation in validated_relations:
        if relation.source_evidence_id not in known_evidence:
            raise ValidationError(
                f"Relation {relation.relation_id!r} references missing evidence "
                f"{relation.source_evidence_id!r}."
            )
        if relation.target_claim_id != claim_id:
            raise ValidationError(
                f"Relation {relation.relation_id!r} references missing claim "
                f"{relation.target_claim_id!r}."
            )
        source = next(
            item for item in validated_evidence
            if item.evidence_id == relation.source_evidence_id
        )
        expected = (
            RelationType.SUPPORTS
            if source.polarity is EvidencePolarity.SUPPORT
            else RelationType.CONTRADICTS
        )
        if relation.relation_type is not expected:
            raise ValidationError(
                f"Relation {relation.relation_id!r} conflicts with source evidence polarity."
            )
    return validated_evidence, validated_relations


def compute_claim_state(
    claim_id: str,
    evidence: Sequence[EvidenceRecord],
    relations: Sequence[RelationRecord] = (),
    *,
    assessment_cycle: Optional[int] = None,
    config: MPRDConfig = FROZEN_CONFIG,
) -> ClaimState:
    """Compute one canonical claim state without mutating caller-owned data."""
    if config != FROZEN_CONFIG:
        raise ConfigurationMismatch(
            "Canonical MPRD_V1 v1.0.1 requires the frozen configuration."
        )
    config.validated()
    claim_id = _require_identifier("claim_id", claim_id)
    packet, relation_packet = validate_packet(claim_id, evidence, relations)

    if assessment_cycle is None:
        assessment_cycle = max((item.cycle for item in packet), default=0)
    if (
        isinstance(assessment_cycle, bool)
        or not isinstance(assessment_cycle, int)
        or assessment_cycle < 0
    ):
        raise ValidationError("assessment_cycle must be a non-negative integer.")

    visible = tuple(
        sorted(
            (item for item in packet if item.cycle <= assessment_cycle),
            key=lambda item: (item.cycle, item.evidence_id),
        )
    )
    visible_ids = {item.evidence_id for item in visible}
    visible_relations = tuple(
        sorted(
            (
                item
                for item in relation_packet
                if item.source_evidence_id in visible_ids
            ),
            key=lambda item: item.relation_id,
        )
    )
    supports = tuple(
        item for item in visible if item.polarity is EvidencePolarity.SUPPORT
    )
    contradictions = tuple(
        item for item in visible
        if item.polarity is EvidencePolarity.CONTRADICTION
    )

    support_strengths = [evidence_strength(item) for item in supports]
    contradiction_strengths = [evidence_strength(item) for item in contradictions]
    mean_support = (
        sum(support_strengths) / len(support_strengths)
        if support_strengths else 0.0
    )
    mean_contradiction = (
        sum(contradiction_strengths) / len(contradiction_strengths)
        if contradiction_strengths else 0.0
    )
    independent_groups = len({item.independence_group for item in supports})
    recurrence_count = len(supports)
    independence_component = clamp(independent_groups / 3.0)
    recurrence_component = clamp(recurrence_count / 4.0)
    relation_balance = (
        clamp(
            (len(supports) - len(contradictions) + len(visible))
            / (2.0 * len(visible))
        )
        if visible else 0.0
    )

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

    rationale = []
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
        rationale.append(
            f"{len(contradictions)} contradicting evidence record(s) integrated."
        )
    rationale.append(f"{independent_groups} independent supporting group(s) represented.")

    state_values = {
        "claim_id": claim_id,
        "assessment_cycle": assessment_cycle,
        "evidence_count": len(visible),
        "support_count": len(supports),
        "contradiction_count": len(contradictions),
        "independent_groups": independent_groups,
        "recurrence_count": recurrence_count,
        "support_score": round(support_score, 8),
        "contradiction_score": round(contradiction_score, 8),
        "adjusted_support": round(adjusted_support, 8),
        "confidence": round(confidence, 8),
        "persistence": round(persistence, 8),
        "status": status,
        "evidence_ids": tuple(item.evidence_id for item in visible),
        "relation_ids": tuple(item.relation_id for item in visible_relations),
        "rationale": tuple(rationale),
    }
    digest_payload = dict(state_values)
    digest_payload["status"] = status.value
    digest_payload["algorithm_version"] = ALGORITHM_VERSION
    digest_payload["schema_version"] = SCHEMA_VERSION
    digest_payload["configuration_digest"] = FROZEN_CONFIG_DIGEST
    return ClaimState(
        **state_values,
        substantive_digest=stable_digest(digest_payload),
    )


def canonical_core_identity(source_path: Optional[str] = None) -> Mapping[str, Any]:
    """Return the frozen configuration and exact source identity."""
    path = Path(source_path).resolve() if source_path else Path(__file__).resolve()
    source_bytes = path.read_bytes()
    return {
        "algorithm_name": ALGORITHM_NAME,
        "algorithm_version": ALGORITHM_VERSION,
        "canonical_source_filename": path.name,
        "canonical_source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "configuration": asdict(FROZEN_CONFIG),
        "configuration_digest": FROZEN_CONFIG_DIGEST,
        "classification_order": list(CLASSIFICATION_ORDER),
        "serialization_schema_version": SCHEMA_VERSION,
        "standard_library_only": True,
    }


def assert_frozen_identity(
    *,
    expected_source_sha256: Optional[str] = None,
    expected_configuration_digest: str = FROZEN_CONFIG_DIGEST,
    source_path: Optional[str] = None,
) -> Mapping[str, Any]:
    """Stop execution when a pre-registered canonical identity does not match."""
    identity = canonical_core_identity(source_path)
    if identity["configuration_digest"] != expected_configuration_digest:
        raise ConfigurationMismatch("CONFIGURATION_MISMATCH: configuration digest differs.")
    if (
        expected_source_sha256 is not None
        and identity["canonical_source_sha256"] != expected_source_sha256
    ):
        raise ConfigurationMismatch("CONFIGURATION_MISMATCH: source hash differs.")
    return identity


__all__ = [
    "ALGORITHM_NAME",
    "ALGORITHM_VERSION",
    "CANONICAL_MODULE_NAME",
    "SCHEMA_VERSION",
    "CLASSIFICATION_ORDER",
    "FROZEN_CONFIG",
    "FROZEN_CONFIG_DIGEST",
    "MPRDError",
    "ValidationError",
    "ConfigurationMismatch",
    "EvidencePolarity",
    "RelationType",
    "ClaimStatus",
    "EvidenceRecord",
    "RelationRecord",
    "MPRDConfig",
    "ClaimState",
    "canonical_json",
    "stable_digest",
    "evidence_strength",
    "validate_packet",
    "compute_claim_state",
    "canonical_core_identity",
    "assert_frozen_identity",
]
