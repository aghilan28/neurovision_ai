"""The immutable source population and its in-memory builder.

``SourcePopulation`` is the single object the intelligence layer reads. It is a
frozen snapshot: once built, its contents cannot change. Every accessor returns
already-stored immutable records, and :meth:`SourcePopulation.integrity_digest`
yields a content hash per kind so callers can assert that source truth was never
modified by any downstream processing (the source-immutability invariant).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from backend.multi_case_intelligence.schemas.base import ArtifactKind, ArtifactRef
from backend.multi_case_intelligence.schemas.determinism import content_hash
from backend.multi_case_intelligence.schemas.source import (
    ClinicalCase,
    Evidence,
    Finding,
    Interpretation,
    Knowledge,
    Patient,
    Review,
    Study,
)


@dataclass(frozen=True, slots=True)
class SourcePopulation:
    """An immutable snapshot of upstream clinical artifacts.

    All collections are tuples (immutable). Indices are built once at
    construction and cached on the frozen instance via ``object.__setattr__``.
    """

    patients: tuple[Patient, ...] = ()
    studies: tuple[Study, ...] = ()
    cases: tuple[ClinicalCase, ...] = ()
    reviews: tuple[Review, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    findings: tuple[Finding, ...] = ()
    interpretations: tuple[Interpretation, ...] = ()
    knowledge: tuple[Knowledge, ...] = ()

    # Cached indices (populated in __post_init__).
    _index: Mapping[tuple[str, str], object] = field(default=None, repr=False, compare=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        index: dict[tuple[str, str], object] = {}
        for rec in self._all_records():
            ref = rec.ref()
            key = ref.key
            if key in index:
                raise ValueError(f"duplicate source artifact id for {key}")
            index[key] = rec
        object.__setattr__(self, "_index", index)

    # -- iteration helpers ------------------------------------------------- #
    def _all_records(self) -> Iterable[object]:
        yield from self.patients
        yield from self.studies
        yield from self.cases
        yield from self.reviews
        yield from self.evidence
        yield from self.findings
        yield from self.interpretations
        yield from self.knowledge

    def collection(self, kind: ArtifactKind) -> tuple[object, ...]:
        """Return the immutable collection for a source ``kind``."""
        return {
            ArtifactKind.PATIENT: self.patients,
            ArtifactKind.STUDY: self.studies,
            ArtifactKind.CASE: self.cases,
            ArtifactKind.REVIEW: self.reviews,
            ArtifactKind.EVIDENCE: self.evidence,
            ArtifactKind.FINDING: self.findings,
            ArtifactKind.INTERPRETATION: self.interpretations,
            ArtifactKind.KNOWLEDGE: self.knowledge,
        }[kind]

    def get(self, ref: ArtifactRef) -> object | None:
        """Resolve a source reference to its record, or ``None``."""
        return self._index.get(ref.key)

    def contains(self, ref: ArtifactRef) -> bool:
        return ref.key in self._index

    # -- relational lookups ------------------------------------------------ #
    def reviews_for_case(self, case_id: str) -> tuple[Review, ...]:
        return tuple(sorted((r for r in self.reviews if r.case_id == case_id), key=lambda r: r.review_id))

    def findings_for_case(self, case_id: str) -> tuple[Finding, ...]:
        return tuple(sorted((f for f in self.findings if f.case_id == case_id), key=lambda f: f.finding_id))

    def findings_for_review(self, review_id: str) -> tuple[Finding, ...]:
        return tuple(sorted((f for f in self.findings if f.review_id == review_id), key=lambda f: f.finding_id))

    def evidence_for_finding(self, finding_id: str) -> tuple[Evidence, ...]:
        return tuple(sorted((e for e in self.evidence if e.finding_id == finding_id), key=lambda e: e.evidence_id))

    def interpretations_for_finding(self, finding_id: str) -> tuple[Interpretation, ...]:
        return tuple(
            sorted(
                (i for i in self.interpretations if i.finding_id == finding_id),
                key=lambda i: i.interpretation_id,
            )
        )

    def knowledge_for_category(self, category) -> tuple[Knowledge, ...]:
        return tuple(
            sorted(
                (k for k in self.knowledge if k.finding_category == category),
                key=lambda k: k.knowledge_id,
            )
        )

    def case(self, case_id: str) -> ClinicalCase | None:
        return self._index.get((ArtifactKind.CASE.value, case_id))  # type: ignore[return-value]

    def patient(self, patient_id: str) -> Patient | None:
        return self._index.get((ArtifactKind.PATIENT.value, patient_id))  # type: ignore[return-value]

    # -- integrity --------------------------------------------------------- #
    def integrity_digest(self) -> Mapping[str, str]:
        """Per-kind content hash of the population (used to prove immutability)."""
        return {
            kind.value: content_hash(
                [rec.ref().content_hash for rec in sorted(self.collection(kind), key=lambda r: r.ref().id)]
            )
            for kind in (
                ArtifactKind.PATIENT,
                ArtifactKind.STUDY,
                ArtifactKind.CASE,
                ArtifactKind.REVIEW,
                ArtifactKind.EVIDENCE,
                ArtifactKind.FINDING,
                ArtifactKind.INTERPRETATION,
                ArtifactKind.KNOWLEDGE,
            )
        }

    def digest(self) -> str:
        """A single content hash over the whole population."""
        return content_hash(self.integrity_digest())

    @property
    def size(self) -> int:
        return sum(1 for _ in self._all_records())


class PopulationBuilder:
    """In-memory reference provider for assembling a :class:`SourcePopulation`.

    This stands in for the persistent V2 case/review/finding/knowledge stores.
    It only *collects* records; it performs no mutation of any record it is
    given. Calling :meth:`build` produces an immutable snapshot.
    """

    def __init__(self) -> None:
        self._patients: list[Patient] = []
        self._studies: list[Study] = []
        self._cases: list[ClinicalCase] = []
        self._reviews: list[Review] = []
        self._evidence: list[Evidence] = []
        self._findings: list[Finding] = []
        self._interpretations: list[Interpretation] = []
        self._knowledge: list[Knowledge] = []

    def add_patient(self, patient: Patient) -> "PopulationBuilder":
        self._patients.append(patient)
        return self

    def add_study(self, study: Study) -> "PopulationBuilder":
        self._studies.append(study)
        return self

    def add_case(self, case: ClinicalCase) -> "PopulationBuilder":
        self._cases.append(case)
        return self

    def add_review(self, review: Review) -> "PopulationBuilder":
        self._reviews.append(review)
        return self

    def add_evidence(self, evidence: Evidence) -> "PopulationBuilder":
        self._evidence.append(evidence)
        return self

    def add_finding(self, finding: Finding) -> "PopulationBuilder":
        self._findings.append(finding)
        return self

    def add_interpretation(self, interpretation: Interpretation) -> "PopulationBuilder":
        self._interpretations.append(interpretation)
        return self

    def add_knowledge(self, knowledge: Knowledge) -> "PopulationBuilder":
        self._knowledge.append(knowledge)
        return self

    def build(self) -> SourcePopulation:
        """Produce an immutable, deterministically-ordered population snapshot."""
        return SourcePopulation(
            patients=tuple(sorted(self._patients, key=lambda r: r.patient_id)),
            studies=tuple(sorted(self._studies, key=lambda r: r.study_id)),
            cases=tuple(sorted(self._cases, key=lambda r: r.case_id)),
            reviews=tuple(sorted(self._reviews, key=lambda r: r.review_id)),
            evidence=tuple(sorted(self._evidence, key=lambda r: r.evidence_id)),
            findings=tuple(sorted(self._findings, key=lambda r: r.finding_id)),
            interpretations=tuple(
                sorted(self._interpretations, key=lambda r: r.interpretation_id)
            ),
            knowledge=tuple(sorted(self._knowledge, key=lambda r: r.knowledge_id)),
        )
