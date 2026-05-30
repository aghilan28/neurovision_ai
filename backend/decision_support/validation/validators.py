"""Decision validators, governance gate, and scope guard.

* :class:`DecisionScopeGuard` — screens any text for clinical-directive language
  (diagnosis/treatment/medication/etc.) that would exceed decision-support scope
  (``docs/PROJECT_SCOPE.md`` O5/O6/O7, R1). This is the mechanical enforcement of
  "No recommendation exceeds decision-support scope".
* :class:`DecisionGovernanceGate` — architecture/quality/context/risk validation
  every decision artifact passes before registry admission.
* :class:`DecisionValidator` — integrity of the whole decision subsystem.
"""

from __future__ import annotations

import re

from backend.decision_support.schemas.decision import (
    DecisionSupportRecord,
    EvidenceBundle,
    GuidanceRecord,
    PrioritizationRecord,
    RiskContext,
)
from backend.multi_case_intelligence.registry.registry import IntelligenceRegistry
from backend.multi_case_intelligence.schemas.base import ArtifactKind, VersionedArtifact
from backend.multi_case_intelligence.validation.validators import (
    ValidationReport,
    ValidationResult,
)

# Artifact kinds the decision layer is permitted to produce (architecture boundary).
DECISION_KINDS = frozenset(
    {
        ArtifactKind.DECISION_CONTEXT,
        ArtifactKind.EVIDENCE_BUNDLE,
        ArtifactKind.RISK_CONTEXT,
        ArtifactKind.PRIORITIZATION,
        ArtifactKind.GUIDANCE,
        ArtifactKind.DECISION_SUPPORT,
        ArtifactKind.DECISION_REPORT,
    }
)

# Clinical-directive lexicon that is OUT OF SCOPE for decision support.
# Word-boundary matched (with optional trailing 's') to avoid false positives on
# common words. Deliberately excludes ambiguous words like "order".
_FORBIDDEN_TERMS = (
    "diagnosis",
    "diagnose",
    "diagnostic",
    "treat",
    "treatment",
    "therapy",
    "therapeutic",
    "prescribe",
    "prescription",
    "medication",
    "medicate",
    "dosage",
    "dose",
    "milligram",
    "administer",
    "contraindication",
)
_FORBIDDEN_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _FORBIDDEN_TERMS) + r")(s)?\b",
    re.IGNORECASE,
)


class DecisionScopeGuard:
    """Screens text and artifacts for out-of-scope clinical-directive language."""

    def scan_text(self, text: str) -> tuple[str, ...]:
        """Return the distinct forbidden terms found in ``text`` (lowercased)."""
        return tuple(sorted({m.group(0).lower() for m in _FORBIDDEN_RE.finditer(text or "")}))

    def scan_artifact(self, artifact: VersionedArtifact) -> tuple[str, ...]:
        """Return forbidden terms found in any human-readable text of ``artifact``."""
        found: set[str] = set()
        for text in self._texts(artifact):
            found.update(self.scan_text(text))
        return tuple(sorted(found))

    def _texts(self, artifact: VersionedArtifact):
        if isinstance(artifact, GuidanceRecord):
            for item in artifact.items:
                yield item.message
                yield item.rationale
        if isinstance(artifact, PrioritizationRecord):
            yield artifact.reason
        if isinstance(artifact, DecisionSupportRecord):
            yield artifact.explanation


class DecisionGovernanceGate:
    """The architecture/quality/context/risk gate for decision artifacts."""

    def __init__(self) -> None:
        self._guard = DecisionScopeGuard()

    def evaluate(
        self, artifact: VersionedArtifact, *, parents: tuple = (), requires_lineage: bool = True
    ) -> ValidationReport:
        results = [
            self._architecture(artifact),
            self._quality(artifact),
            self._context(artifact, parents, requires_lineage),
            self._risk(artifact),
        ]
        return ValidationReport(scope=f"decision_gate:{artifact.KIND.value}:{artifact.id}", results=tuple(results))

    def _architecture(self, artifact: VersionedArtifact) -> ValidationResult:
        ok = artifact.KIND in DECISION_KINDS
        return ValidationResult(
            "architecture_validation", ok,
            "" if ok else f"{artifact.KIND.value} is not a decision-producible kind",
        )

    def _quality(self, artifact: VersionedArtifact) -> ValidationResult:
        problems = _structural_problems(artifact)
        return ValidationResult("quality_validation", not problems, "; ".join(problems))

    def _context(self, artifact: VersionedArtifact, parents: tuple, requires_lineage: bool) -> ValidationResult:
        if not requires_lineage:
            return ValidationResult("context_validation", True, "lineage not required")
        ok = len(parents) > 0
        return ValidationResult(
            "context_validation", ok, "" if ok else "artifact has no lineage parents (untraceable)"
        )

    def _risk(self, artifact: VersionedArtifact) -> ValidationResult:
        # Scope guard is the decision-layer's "risk" validation: it ensures no
        # artifact carries out-of-scope clinical-directive content.
        forbidden = self._guard.scan_artifact(artifact)
        ratio = _ratio_problems(artifact)
        problems = list(ratio)
        if forbidden:
            problems.append(f"out-of-scope clinical-directive language: {', '.join(forbidden)}")
        return ValidationResult("risk_validation", not problems, "; ".join(problems))


def _structural_problems(artifact: VersionedArtifact) -> list[str]:
    problems: list[str] = []
    if artifact.version < 1:
        problems.append("version must be >= 1")
    if isinstance(artifact, EvidenceBundle):
        if len(artifact.items) != len(artifact.ranking):
            problems.append("evidence bundle items/ranking length mismatch")
        ranks = [it.rank for it in artifact.items]
        if ranks != list(range(1, len(ranks) + 1)):
            problems.append("evidence bundle ranks are not 1..n contiguous")
        if tuple(it.evidence_ref.id for it in artifact.items) != artifact.ranking:
            problems.append("evidence bundle item order disagrees with ranking")
    if isinstance(artifact, PrioritizationRecord):
        total = sum(f.contribution for f in artifact.factors)
        if abs(total - artifact.score) > 1e-6:
            problems.append("prioritization factor contributions do not sum to score")
    if isinstance(artifact, RiskContext):
        agg = sum(c.value for c in artifact.components) / len(artifact.components) if artifact.components else 0.0
        if abs(round(agg, 9) - artifact.aggregate) > 1e-6:
            problems.append("risk aggregate does not match component mean")
    return problems


def _ratio_problems(artifact: VersionedArtifact) -> list[str]:
    problems: list[str] = []
    if isinstance(artifact, RiskContext):
        if not 0.0 <= artifact.aggregate <= 1.0:
            problems.append("risk aggregate out of [0,1]")
        for c in artifact.components:
            if not 0.0 <= c.value <= 1.0:
                problems.append(f"risk component {c.name} out of [0,1]")
    if isinstance(artifact, PrioritizationRecord):
        if not 0.0 <= artifact.score <= 1.0:
            problems.append("prioritization score out of [0,1]")
    if isinstance(artifact, EvidenceBundle):
        for it in artifact.items:
            if not 0.0 <= it.confidence <= 1.0:
                problems.append(f"evidence confidence out of [0,1] for {it.evidence_ref.id}")
    return problems


class DecisionValidator:
    """Validates integrity of the decision subsystem state."""

    def __init__(self) -> None:
        self._guard = DecisionScopeGuard()

    def validate(self, registry: IntelligenceRegistry, *, scope: str = "decision_support") -> ValidationReport:
        results = [
            self._audit_integrity(registry),
            self._registry_integrity(registry),
            self._lineage_integrity(registry),
            self._version_integrity(registry),
            self._evidence_integrity(registry),
            self._guidance_integrity(registry),
            self._risk_integrity(registry),
            self._scope_integrity(registry),
        ]
        return ValidationReport(scope=scope, results=tuple(results))

    def _audit_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        ok = registry.audit.verify()
        return ValidationResult("audit_integrity", ok, "" if ok else "audit hash chain is broken")

    def _registry_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems = [
            f"content hash mismatch for {e.ref.key} v{e.version}"
            for e in registry.all_versions()
            if e.ref.content_hash != e.artifact.compute_hash()
        ]
        return ValidationResult("registry_integrity", not problems, "; ".join(problems[:5]))

    def _lineage_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for e in registry.all_versions():
            rec = registry.lineage.get(e.ref)
            if rec is None or not rec.roots:
                problems.append(f"missing/empty lineage for {e.ref.key} v{e.version}")
        return ValidationResult("lineage_integrity", not problems, "; ".join(problems[:5]))

    def _version_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for entry in registry.all_entries():
            history = registry.history(entry.ref.kind, entry.ref.id)
            for i, e in enumerate(history, start=1):
                if e.version != i:
                    problems.append(f"non-monotonic version for {entry.ref.key}")
            hashes = [e.content_hash for e in history]
            if len(hashes) != len(set(hashes)):
                problems.append(f"duplicate content across versions for {entry.ref.key}")
        return ValidationResult("version_integrity", not problems, "; ".join(problems[:5]))

    def _evidence_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for e in registry.all_versions():
            if isinstance(e.artifact, EvidenceBundle):
                problems.extend(_structural_problems(e.artifact))
                problems.extend(_ratio_problems(e.artifact))
        return ValidationResult("evidence_integrity", not problems, "; ".join(problems[:5]))

    def _guidance_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for e in registry.all_versions():
            if isinstance(e.artifact, GuidanceRecord):
                if not e.artifact.items:
                    problems.append(f"guidance {e.artifact.id} has no items")
        return ValidationResult("guidance_integrity", not problems, "; ".join(problems[:5]))

    def _risk_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for e in registry.all_versions():
            if isinstance(e.artifact, RiskContext):
                problems.extend(_structural_problems(e.artifact))
                problems.extend(_ratio_problems(e.artifact))
        return ValidationResult("risk_integrity", not problems, "; ".join(problems[:5]))

    def _scope_integrity(self, registry: IntelligenceRegistry) -> ValidationResult:
        problems: list[str] = []
        for e in registry.all_versions():
            forbidden = self._guard.scan_artifact(e.artifact)
            if forbidden:
                problems.append(f"{e.ref.key}: {', '.join(forbidden)}")
        return ValidationResult(
            "decision_scope_integrity", not problems,
            "out-of-scope clinical-directive language found: " + "; ".join(problems[:5]) if problems else "",
        )
