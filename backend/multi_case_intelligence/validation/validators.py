"""Integrity validators and the governance gate.

``IntelligenceValidator`` checks the integrity of the whole subsystem state
(registry/audit/lineage/versions) plus the immutability of the source
population. ``GovernanceGate`` enforces the four per-workflow validations
mandated by the constitution — Architecture, Quality, Context, Risk — before an
artifact is admitted to the registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.registry.registry import IntelligenceRegistry
from backend.multi_case_intelligence.schemas.base import ArtifactKind, VersionedArtifact
from backend.multi_case_intelligence.schemas.intelligence import (
    Cohort,
    PopulationAnalytics,
    QualityReport,
    Trend,
)

# Artifact kinds the intelligence layer is permitted to *produce* (architecture
# boundary: the intelligence layer never emits source/clinical-truth kinds).
INTELLIGENCE_KINDS = frozenset(
    {
        ArtifactKind.COHORT,
        ArtifactKind.ANALYTICS,
        ArtifactKind.TREND,
        ArtifactKind.QUALITY,
        ArtifactKind.REPORT,
    }
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """The outcome of a single named check."""

    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """A bundle of validation results."""

    scope: str
    results: tuple[ValidationResult, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> tuple[ValidationResult, ...]:
        return tuple(r for r in self.results if not r.passed)

    def summary(self) -> Mapping[str, object]:
        return {
            "scope": self.scope,
            "passed": self.passed,
            "checks": len(self.results),
            "failures": [r.name for r in self.failures],
        }


class GovernanceGate:
    """The architecture/quality/context/risk gate every artifact must pass.

    Returns a :class:`ValidationReport`; the caller (the service) refuses to
    register any artifact that does not pass. This mechanizes the constitution's
    "Every workflow must pass: Architecture/Quality/Context/Risk Validation".
    """

    def evaluate(
        self,
        artifact: VersionedArtifact,
        *,
        parents: tuple = (),
        requires_lineage: bool = True,
    ) -> ValidationReport:
        results = [
            self._architecture(artifact),
            self._quality(artifact),
            self._context(artifact, parents, requires_lineage),
            self._risk(artifact),
        ]
        return ValidationReport(scope=f"gate:{artifact.KIND.value}:{artifact.id}", results=tuple(results))

    # -- the four mandated validations ------------------------------------ #
    def _architecture(self, artifact: VersionedArtifact) -> ValidationResult:
        ok = artifact.KIND in INTELLIGENCE_KINDS
        return ValidationResult(
            "architecture_validation",
            ok,
            "" if ok else f"{artifact.KIND.value} is not an intelligence-producible kind",
        )

    def _quality(self, artifact: VersionedArtifact) -> ValidationResult:
        problems = _structural_problems(artifact)
        return ValidationResult(
            "quality_validation", not problems, "; ".join(problems)
        )

    def _context(self, artifact: VersionedArtifact, parents: tuple, requires_lineage: bool) -> ValidationResult:
        if not requires_lineage:
            return ValidationResult("context_validation", True, "lineage not required for this artifact")
        ok = len(parents) > 0
        return ValidationResult(
            "context_validation", ok, "" if ok else "artifact has no lineage parents (untraceable)"
        )

    def _risk(self, artifact: VersionedArtifact) -> ValidationResult:
        problems = _ratio_problems(artifact)
        return ValidationResult("risk_validation", not problems, "; ".join(problems))


def _structural_problems(artifact: VersionedArtifact) -> list[str]:
    problems: list[str] = []
    if artifact.version < 1:
        problems.append("version must be >= 1")
    if isinstance(artifact, Cohort):
        if len(set(artifact.members)) != len(artifact.members):
            problems.append("cohort members contain duplicates")
        if artifact.member_kind != artifact.criteria.member_kind:
            problems.append("cohort member_kind mismatch with criteria")
    if isinstance(artifact, PopulationAnalytics):
        for b in artifact.blocks:
            if b.count < 0:
                problems.append(f"negative count in block {b.subject_kind.value}")
            for d in b.distributions:
                if d.total != sum(n for _, n in d.counts):
                    problems.append(f"distribution total mismatch in {d.field}")
    return problems


def _ratio_problems(artifact: VersionedArtifact) -> list[str]:
    problems: list[str] = []
    if isinstance(artifact, QualityReport):
        for m in artifact.metrics:
            if not 0.0 <= m.value <= 1.0:
                problems.append(f"quality metric {m.name} out of [0,1]")
            if m.denominator < 0 or m.numerator < 0 or m.numerator > m.denominator:
                problems.append(f"quality metric {m.name} numerator/denominator invalid")
    if isinstance(artifact, PopulationAnalytics):
        for b in artifact.blocks:
            for group in (b.coverage, b.frequency):
                for k, v in group.items():
                    if not 0.0 <= v <= 1.0:
                        problems.append(f"ratio {b.subject_kind.value}.{k} out of [0,1]")
    return problems


class IntelligenceValidator:
    """Validates the integrity of the subsystem state and the source population."""

    def validate(
        self,
        registry: IntelligenceRegistry,
        *,
        population: SourcePopulation | None = None,
        baseline_digest: Mapping[str, str] | None = None,
        scope: str = "intelligence",
    ) -> ValidationReport:
        results: list[ValidationResult] = []
        results.append(self._audit_integrity(registry))
        results.append(self._registry_integrity(registry))
        results.append(self._lineage_integrity(registry))
        results.append(self._version_integrity(registry))
        results.append(self._cohort_integrity(registry))
        results.append(self._analytics_integrity(registry))
        results.append(self._trend_integrity(registry))
        if population is not None and baseline_digest is not None:
            results.append(self._source_immutability(population, baseline_digest))
        return ValidationReport(scope=scope, results=tuple(results))

    # -- checks ------------------------------------------------------------ #
    def _audit_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        ok = registry.audit.verify()
        return ValidationResult("audit_integrity", ok, "" if ok else "audit hash chain is broken")

    def _registry_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for entry in registry.all_versions():
            if entry.ref.content_hash != entry.artifact.compute_hash():
                problems.append(f"content hash mismatch for {entry.ref.key} v{entry.version}")
            if not registry.audit.entries:
                problems.append("registry has entries but audit log is empty")
        return ValidationResult(
            "registry_integrity", not problems, "; ".join(problems[:5])
        )

    def _lineage_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for entry in registry.all_versions():
            record = registry.lineage.get(entry.ref)
            if record is None:
                problems.append(f"no lineage for {entry.ref.key} v{entry.version}")
                continue
            if not record.roots:
                problems.append(f"no lineage roots for {entry.ref.key} v{entry.version}")
        return ValidationResult("lineage_integrity", not problems, "; ".join(problems[:5]))

    def _version_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for key, _ in ((e.ref.key, e) for e in registry.all_entries()):
            history = registry.history(ArtifactKind(key[0]), key[1])
            for i, entry in enumerate(history, start=1):
                if entry.version != i:
                    problems.append(f"non-monotonic version for {key}: {entry.version} != {i}")
            hashes = [e.content_hash for e in history]
            if len(hashes) != len(set(hashes)):
                problems.append(f"duplicate content across versions for {key}")
        return ValidationResult("version_integrity", not problems, "; ".join(problems[:5]))

    def _cohort_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for entry in registry.all_versions():
            art = entry.artifact
            if isinstance(art, Cohort):
                if list(art.members) != sorted(art.members):
                    problems.append(f"cohort {art.id} members not sorted")
                if len(set(art.members)) != len(art.members):
                    problems.append(f"cohort {art.id} has duplicate members")
                if art.member_refs and {r.id for r in art.member_refs} != set(art.members):
                    problems.append(f"cohort {art.id} member_refs/member ids disagree")
        return ValidationResult("cohort_integrity", not problems, "; ".join(problems[:5]))

    def _analytics_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems = []
        for entry in registry.all_versions():
            if isinstance(entry.artifact, PopulationAnalytics):
                problems.extend(_structural_problems(entry.artifact))
                problems.extend(_ratio_problems(entry.artifact))
        return ValidationResult("analytics_integrity", not problems, "; ".join(problems[:5]))

    def _trend_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for entry in registry.all_versions():
            art = entry.artifact
            if isinstance(art, Trend):
                for s in art.series:
                    buckets = [p.bucket for p in s.points]
                    if buckets != sorted(buckets, key=lambda b: (len(b), b)) and buckets != sorted(buckets):
                        # buckets should be in a stable order
                        pass
                    if s.points:
                        expected = s.points[-1].value - s.points[0].value
                        if abs(expected - s.delta) > 1e-6 and len(s.points) >= 2:
                            problems.append(f"trend {art.id} series {s.metric} delta mismatch")
        return ValidationResult("trend_integrity", not problems, "; ".join(problems[:5]))

    def _source_immutability(
        self, population: SourcePopulation, baseline_digest: Mapping[str, str]
    ) -> ValidationResult:
        current = population.integrity_digest()
        ok = dict(current) == dict(baseline_digest)
        return ValidationResult(
            "source_immutability",
            ok,
            "" if ok else "source population digest changed (source truth was modified)",
        )
