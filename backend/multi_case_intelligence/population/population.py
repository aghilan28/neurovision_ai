"""Immutable multi-case population snapshot.

``PopulationView`` is the read-only collection of real clinical aggregates the
intelligence layer reasons over: Cases (V2-P1), Reviews (V2-P2), Findings &
Interpretations (V2-P3), and Knowledge concepts/terms (V2-P4). It builds
convenience indices and exposes an ``integrity_digest`` so callers can *prove*
the intelligence layer never mutated source truth.

The view holds references to the real aggregates; it never copies or alters them.
Equality/hash of source truth is captured via each aggregate's ``signature`` /
``state_signature`` (already defined by the source layers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from backend.clinical_cases.models.domain import Case
from backend.clinical_review.models.domain import Review
from backend.clinical_findings.models.domain import Finding, FindingInterpretation
from backend.clinical_knowledge.models.domain import Concept, Term


def finding_confidence(finding: Finding) -> Optional[float]:
    """Best recorded (calibrated) evidence confidence on a finding, or None.

    Confidence is *read* from the recorded V1 evidence (never recomputed),
    honouring AP-4/NR-4 (uncertainty preserved, never invented).
    """
    vals = [e.evidence_confidence for e in finding.evidence if e.evidence_confidence is not None]
    return max(vals) if vals else None


@dataclass(frozen=True)
class PopulationView:
    """An immutable snapshot of the multi-case population."""

    cases: tuple[Case, ...] = ()
    reviews: tuple[Review, ...] = ()
    findings: tuple[Finding, ...] = ()
    interpretations: tuple[FindingInterpretation, ...] = ()
    concepts: tuple[Concept, ...] = ()
    terms: tuple[Term, ...] = ()
    _by: dict = field(default=None, repr=False, compare=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        idx = {
            "case": {c.case_id: c for c in self.cases},
            "review": {r.review_id: r for r in self.reviews},
            "finding": {f.finding_id: f for f in self.findings},
            "interpretation": {i.interpretation_id: i for i in self.interpretations},
            "concept": {c.concept_id: c for c in self.concepts},
            "term": {t.term_id: t for t in self.terms},
        }
        object.__setattr__(self, "_by", idx)

    # --- relational lookups ---------------------------------------------------
    def reviews_for_case(self, case_id: str) -> tuple[Review, ...]:
        return tuple(sorted((r for r in self.reviews if r.case_id == case_id),
                            key=lambda r: r.review_id))

    def findings_for_case(self, case_id: str) -> tuple[Finding, ...]:
        return tuple(sorted((f for f in self.findings if f.case_id == case_id),
                            key=lambda f: f.finding_id))

    def findings_for_review(self, review_id: str) -> tuple[Finding, ...]:
        return tuple(sorted((f for f in self.findings if f.review_id == review_id),
                            key=lambda f: f.finding_id))

    def interpretations_for_finding(self, finding_id: str) -> tuple[FindingInterpretation, ...]:
        return tuple(sorted((i for i in self.interpretations if i.finding_id == finding_id),
                            key=lambda i: i.interpretation_id))

    def case(self, case_id: str) -> Optional[Case]:
        return self._by["case"].get(case_id)

    def patient_ids(self) -> tuple[str, ...]:
        return tuple(sorted({c.patient_id for c in self.cases}))

    # --- knowledge vocabulary -------------------------------------------------
    def knowledge_terms(self) -> frozenset[str]:
        """Lower-cased set of concept names + term strings (the knowledge vocabulary)."""
        vocab = {c.name.lower() for c in self.concepts}
        vocab |= {t.term.lower() for t in self.terms}
        vocab |= {rt.lower() for c in self.concepts for rt in c.related_terms}
        return frozenset(vocab)

    def category_is_known(self, category: str) -> bool:
        return bool(category) and category.lower() in self.knowledge_terms()

    # --- integrity ------------------------------------------------------------
    def integrity_digest(self) -> dict:
        """Per-kind content digest of the source population (immutability proof)."""
        return {
            "case": hash_obj([c.state_signature() for c in
                              sorted(self.cases, key=lambda c: c.case_id)]),
            "review": hash_obj([r.state_signature() for r in
                                sorted(self.reviews, key=lambda r: r.review_id)]),
            "finding": hash_obj([f.state_signature() for f in
                                 sorted(self.findings, key=lambda f: f.finding_id)]),
            "interpretation": hash_obj([i.signature() for i in
                                        sorted(self.interpretations, key=lambda i: i.interpretation_id)]),
            "concept": hash_obj([c.signature() for c in
                                 sorted(self.concepts, key=lambda c: c.concept_id)]),
            "term": hash_obj([t.signature() for t in
                              sorted(self.terms, key=lambda t: t.term_id)]),
        }

    def digest(self) -> str:
        return hash_obj(self.integrity_digest())

    @property
    def size(self) -> int:
        return (len(self.cases) + len(self.reviews) + len(self.findings)
                + len(self.interpretations) + len(self.concepts) + len(self.terms))


class PopulationBuilder:
    """Assembles an immutable :class:`PopulationView` from real aggregates.

    The builder only *collects* references to aggregates the caller already holds
    (e.g. from ``CaseService``/``ReviewService``/``FindingService``); it never
    mutates them.
    """

    def __init__(self) -> None:
        self._cases: list = []
        self._reviews: list = []
        self._findings: list = []
        self._interpretations: list = []
        self._concepts: list = []
        self._terms: list = []

    def add_case(self, case) -> "PopulationBuilder":
        self._cases.append(case); return self

    def add_review(self, review) -> "PopulationBuilder":
        self._reviews.append(review); return self

    def add_finding(self, finding) -> "PopulationBuilder":
        self._findings.append(finding); return self

    def add_interpretation(self, interp) -> "PopulationBuilder":
        self._interpretations.append(interp); return self

    def add_knowledge_service(self, knowledge_service) -> "PopulationBuilder":
        """Pull all registered concepts + terms from a ``KnowledgeService``."""
        for cid in knowledge_service.concepts.list_concepts():
            self._concepts.append(knowledge_service.concepts.get(cid))
        for tid in knowledge_service.terminology.list_terms():
            self._terms.append(knowledge_service.terminology.get(tid))
        return self

    def build(self) -> PopulationView:
        return PopulationView(
            cases=tuple(sorted(self._cases, key=lambda c: c.case_id)),
            reviews=tuple(sorted(self._reviews, key=lambda r: r.review_id)),
            findings=tuple(sorted(self._findings, key=lambda f: f.finding_id)),
            interpretations=tuple(sorted(self._interpretations, key=lambda i: i.interpretation_id)),
            concepts=tuple(sorted(self._concepts, key=lambda c: c.concept_id)),
            terms=tuple(sorted(self._terms, key=lambda t: t.term_id)),
        )
