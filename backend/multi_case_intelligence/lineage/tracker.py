"""Deterministic lineage tracking.

The tracker stores one :class:`LineageRecord` per artifact ``(kind, id)``. Roots
are computed by walking parent links transitively until reaching artifacts with
no tracked parents (the source roots). Because the graph is built only from
explicit parent references and never mutated, traversal is deterministic.
"""

from __future__ import annotations

from backend.multi_case_intelligence.schemas.base import ArtifactRef
from backend.multi_case_intelligence.schemas.events import LineageEdge, LineageRecord


class IntelligenceLineageTracker:
    """Maintains the provenance graph for intelligence artifacts."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], LineageRecord] = {}

    def register(
        self,
        subject: ArtifactRef,
        parents: tuple[ArtifactRef, ...] = (),
        *,
        relation: str = "derived_from",
    ) -> LineageRecord:
        """Record the provenance of ``subject`` given its immediate ``parents``.

        Roots are resolved transitively: a parent that is itself tracked
        contributes *its* roots; a parent that is not tracked (a source artifact)
        is itself a root.
        """
        edges = tuple(LineageEdge(child=subject, parent=p, relation=relation) for p in parents)
        roots = self._resolve_roots(parents)
        record = LineageRecord(subject=subject, edges=edges, roots=roots)
        self._records[subject.key] = record
        return record

    def _resolve_roots(self, parents: tuple[ArtifactRef, ...]) -> tuple[ArtifactRef, ...]:
        roots: list[ArtifactRef] = []
        seen: set[tuple[str, str]] = set()
        for parent in parents:
            for root in self._roots_of(parent, set()):
                if root.key not in seen:
                    seen.add(root.key)
                    roots.append(root)
        # Deterministic ordering of roots.
        roots.sort(key=lambda r: (r.kind.value, r.id))
        return tuple(roots)

    def _roots_of(self, ref: ArtifactRef, visiting: set[tuple[str, str]]) -> list[ArtifactRef]:
        rec = self._records.get(ref.key)
        if rec is None or not rec.edges:
            return [ref]  # untracked or parentless -> this is a root
        if ref.key in visiting:
            return [ref]  # cycle guard (should never happen for a DAG)
        visiting = visiting | {ref.key}
        out: list[ArtifactRef] = []
        for parent in rec.parents():
            out.extend(self._roots_of(parent, visiting))
        return out

    # -- read-only access -------------------------------------------------- #
    def get(self, ref: ArtifactRef) -> LineageRecord | None:
        return self._records.get(ref.key)

    def has(self, ref: ArtifactRef) -> bool:
        return ref.key in self._records

    def trace(self, ref: ArtifactRef) -> tuple[ArtifactRef, ...]:
        """Return the transitive set of ancestors of ``ref`` (deterministic)."""
        rec = self._records.get(ref.key)
        if rec is None:
            return ()
        out: list[ArtifactRef] = []
        seen: set[tuple[str, str]] = set()
        stack = list(rec.parents())
        while stack:
            cur = stack.pop()
            if cur.key in seen:
                continue
            seen.add(cur.key)
            out.append(cur)
            parent_rec = self._records.get(cur.key)
            if parent_rec is not None:
                stack.extend(parent_rec.parents())
        out.sort(key=lambda r: (r.kind.value, r.id))
        return tuple(out)

    def roots(self, ref: ArtifactRef) -> tuple[ArtifactRef, ...]:
        rec = self._records.get(ref.key)
        return rec.roots if rec else ()

    def __len__(self) -> int:
        return len(self._records)


def seed_population_lineage(tracker: IntelligenceLineageTracker, population) -> None:
    """Seed a lineage tracker with a source population's provenance chain.

    Registers Patient -> Case -> Review -> Finding -> Interpretation/Evidence and
    Knowledge (as a root) so that any downstream artifact whose parents are these
    source refs resolves transitively to patient roots. Source artifacts are only
    recorded in the *lineage tracker*, never in any registry.
    """
    for patient in population.patients:
        tracker.register(patient.ref(), ())
    for case in population.cases:
        patient = population.patient(case.patient_id)
        tracker.register(case.ref(), (patient.ref(),) if patient else ())
    for review in population.reviews:
        case = population.case(review.case_id)
        tracker.register(review.ref(), (case.ref(),) if case else ())
    findings_by_id = {f.finding_id: f for f in population.findings}
    reviews_by_id = {r.review_id: r for r in population.reviews}
    for finding in population.findings:
        review = reviews_by_id.get(finding.review_id)
        tracker.register(finding.ref(), (review.ref(),) if review else ())
    for interp in population.interpretations:
        finding = findings_by_id.get(interp.finding_id)
        tracker.register(interp.ref(), (finding.ref(),) if finding else ())
    for ev in population.evidence:
        parents: tuple = ()
        if ev.finding_id is not None and ev.finding_id in findings_by_id:
            parents = (findings_by_id[ev.finding_id].ref(),)
        else:
            case = population.case(ev.case_id)
            parents = (case.ref(),) if case else ()
        tracker.register(ev.ref(), parents)
    for knowledge in population.knowledge:
        tracker.register(knowledge.ref(), ())
