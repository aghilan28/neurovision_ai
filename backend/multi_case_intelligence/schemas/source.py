"""Immutable source-artifact contracts (the integration boundary).

These dataclasses are the **contract** by which V2-P5/P6 read upstream clinical
truth. They model the artifacts owned by earlier phases:

* Version 2-P1 Clinical Case Foundation  -> :class:`Patient`, :class:`ClinicalCase`, :class:`Study`
* Version 2-P2 Clinical Review Workflow  -> :class:`Review`
* Version 2-P3 Findings & Interpretation -> :class:`Evidence`, :class:`Finding`, :class:`Interpretation`
* Version 2-P4 Clinical Knowledge Layer  -> :class:`Knowledge`
* Version 1 inference/calibration/coverage/risk -> :class:`UncertaintySignal`, :class:`RiskAttributes`

This subsystem **reads** these records and **never writes** them. They are all
``frozen`` (immutable) and content-hashable so the intelligence/decision layers
can prove that source truth was not altered (see the source-immutability
validators).

In a fully populated repository these types would be *imported from* the
``backend`` case/review/finding/knowledge modules and the ``ml``/``evaluation``
layers. They are defined here as an explicit, minimal integration port because
those modules are not yet materialized on disk; the field set is intentionally a
faithful subset of the documented contracts and nothing more.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from backend.multi_case_intelligence.schemas.base import ArtifactKind, ArtifactRef
from backend.multi_case_intelligence.schemas.determinism import content_hash, quantize


class FindingCategory(str, Enum):
    """ACNS-aligned categories (see ``docs/GLOSSARY.md``). Decision-support only."""

    SZ = "SZ"
    LPD = "LPD"
    GPD = "GPD"
    LRDA = "LRDA"
    GRDA = "GRDA"
    OTHER = "Other"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    SIGNED_OFF = "signed_off"


@dataclass(frozen=True, slots=True)
class UncertaintySignal:
    """Calibrated uncertainty carried from the Version 1 ML/evaluation layers.

    This is how AP-4 (uncertainty-aware) flows *into* the intelligence/decision
    layers. The intelligence layer preserves it and never flattens it (NR-4).

    * ``confidence``        — calibrated point confidence in ``[0, 1]``.
    * ``prediction_set``    — conformal prediction set (the classes not excluded).
    * ``coverage_target``   — target coverage of the conformal method in ``[0, 1]``.
    * ``empirical_coverage``— measured coverage in ``[0, 1]`` (from evaluation).
    * ``calibration_error`` — measured calibration error in ``[0, 1]``.
    * ``abstained``         — whether the model abstained/escalated.
    """

    confidence: float
    prediction_set: tuple[str, ...] = ()
    coverage_target: float = 0.9
    empirical_coverage: float = 0.9
    calibration_error: float = 0.0
    abstained: bool = False

    def __post_init__(self) -> None:
        for name in (
            "confidence",
            "coverage_target",
            "empirical_coverage",
            "calibration_error",
        ):
            v = getattr(self, name)
            if not 0.0 <= float(v) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v!r}")
            object.__setattr__(self, name, quantize(float(v)))


@dataclass(frozen=True, slots=True)
class RiskAttributes:
    """Version-1-derived risk context inputs (decision-support framing).

    These are *uncertainty/coverage* risks about the analysis, not clinical risk
    scores. All values are normalized to ``[0, 1]`` where higher means "more
    reason for a human to look closely".
    """

    inference_risk: float = 0.0
    coverage_risk: float = 0.0
    calibration_risk: float = 0.0

    def __post_init__(self) -> None:
        for name in ("inference_risk", "coverage_risk", "calibration_risk"):
            v = getattr(self, name)
            if not 0.0 <= float(v) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v!r}")
            object.__setattr__(self, name, quantize(float(v)))


def _ref(kind: ArtifactKind, id_: str, payload: Mapping[str, Any]) -> ArtifactRef:
    return ArtifactRef(kind=kind, id=id_, content_hash=content_hash(payload), version=1)


@dataclass(frozen=True, slots=True)
class Patient:
    """A patient (the lineage root). Patient-disjoint identity is sacrosanct."""

    patient_id: str
    site: str = "unknown"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    KIND = ArtifactKind.PATIENT

    def ref(self) -> ArtifactRef:
        return _ref(self.KIND, self.patient_id, {"site": self.site})


@dataclass(frozen=True, slots=True)
class Study:
    """An EEG study/recording belonging to a case."""

    study_id: str
    case_id: str
    patient_id: str
    montage: str = "unknown"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    KIND = ArtifactKind.STUDY

    def ref(self) -> ArtifactRef:
        return _ref(
            self.KIND,
            self.study_id,
            {"case_id": self.case_id, "patient_id": self.patient_id, "montage": self.montage},
        )


@dataclass(frozen=True, slots=True)
class ClinicalCase:
    """A clinical case for a patient (V2-P1)."""

    case_id: str
    patient_id: str
    site: str = "unknown"
    status: str = "open"
    ordinal: int = 0  # logical sequence index used by deterministic trend bucketing
    metadata: Mapping[str, Any] = field(default_factory=dict)
    KIND = ArtifactKind.CASE

    def ref(self) -> ArtifactRef:
        return _ref(
            self.KIND,
            self.case_id,
            {"patient_id": self.patient_id, "site": self.site, "status": self.status},
        )


@dataclass(frozen=True, slots=True)
class Review:
    """A clinical review of a case (V2-P2)."""

    review_id: str
    case_id: str
    patient_id: str
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_role: str = "neurophysiologist"
    completeness: float = 0.0  # [0,1] fraction of required review steps complete
    metadata: Mapping[str, Any] = field(default_factory=dict)
    KIND = ArtifactKind.REVIEW

    def __post_init__(self) -> None:
        if not isinstance(self.status, ReviewStatus):
            object.__setattr__(self, "status", ReviewStatus(self.status))
        if not 0.0 <= float(self.completeness) <= 1.0:
            raise ValueError("review completeness must be in [0, 1]")
        object.__setattr__(self, "completeness", quantize(float(self.completeness)))

    @property
    def is_finalized(self) -> bool:
        return self.status in (ReviewStatus.COMPLETED, ReviewStatus.SIGNED_OFF)

    def ref(self) -> ArtifactRef:
        return _ref(
            self.KIND,
            self.review_id,
            {
                "case_id": self.case_id,
                "patient_id": self.patient_id,
                "status": self.status.value,
                "completeness": self.completeness,
            },
        )


@dataclass(frozen=True, slots=True)
class Evidence:
    """A piece of evidence supporting a finding (V2-P3).

    Evidence carries the Version-1 calibrated uncertainty (``signal``). "No
    evidence may be hidden" — the decision layer surfaces every evidence item.
    """

    evidence_id: str
    case_id: str
    patient_id: str
    finding_id: str | None = None
    modality: str = "eeg_segment"
    signal: UncertaintySignal | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    KIND = ArtifactKind.EVIDENCE

    def ref(self) -> ArtifactRef:
        return _ref(
            self.KIND,
            self.evidence_id,
            {
                "case_id": self.case_id,
                "patient_id": self.patient_id,
                "finding_id": self.finding_id,
                "modality": self.modality,
                "signal": self.signal,  # canonicalized by the determinism layer
            },
        )


@dataclass(frozen=True, slots=True)
class Finding:
    """A clinical finding produced during review (V2-P3)."""

    finding_id: str
    review_id: str
    case_id: str
    patient_id: str
    category: FindingCategory = FindingCategory.OTHER
    signal: UncertaintySignal | None = None
    risk: RiskAttributes | None = None
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    KIND = ArtifactKind.FINDING

    def __post_init__(self) -> None:
        if not isinstance(self.category, FindingCategory):
            object.__setattr__(self, "category", FindingCategory(self.category))

    def ref(self) -> ArtifactRef:
        sig = self.signal
        return _ref(
            self.KIND,
            self.finding_id,
            {
                "review_id": self.review_id,
                "case_id": self.case_id,
                "patient_id": self.patient_id,
                "category": self.category.value,
                "confidence": None if sig is None else sig.confidence,
                "evidence_ids": sorted(self.evidence_ids),
            },
        )


@dataclass(frozen=True, slots=True)
class Interpretation:
    """A clinician/structured interpretation of a finding (V2-P3)."""

    interpretation_id: str
    finding_id: str
    case_id: str
    patient_id: str
    completeness: float = 0.0
    summary: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    KIND = ArtifactKind.INTERPRETATION

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.completeness) <= 1.0:
            raise ValueError("interpretation completeness must be in [0, 1]")
        object.__setattr__(self, "completeness", quantize(float(self.completeness)))

    def ref(self) -> ArtifactRef:
        return _ref(
            self.KIND,
            self.interpretation_id,
            {
                "finding_id": self.finding_id,
                "case_id": self.case_id,
                "patient_id": self.patient_id,
                "completeness": self.completeness,
            },
        )


@dataclass(frozen=True, slots=True)
class Knowledge:
    """A clinical-knowledge artifact (V2-P4) linked to a finding category/topic."""

    knowledge_id: str
    topic: str
    finding_category: FindingCategory | None = None
    references: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    KIND = ArtifactKind.KNOWLEDGE

    def __post_init__(self) -> None:
        if self.finding_category is not None and not isinstance(
            self.finding_category, FindingCategory
        ):
            object.__setattr__(
                self, "finding_category", FindingCategory(self.finding_category)
            )

    def ref(self) -> ArtifactRef:
        return _ref(
            self.KIND,
            self.knowledge_id,
            {
                "topic": self.topic,
                "finding_category": None
                if self.finding_category is None
                else self.finding_category.value,
                "references": sorted(self.references),
            },
        )
