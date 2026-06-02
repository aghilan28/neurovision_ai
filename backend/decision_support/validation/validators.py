"""Decision validators, governance gate, and scope guard (V2-P6).

* :class:`DecisionScopeGuard` — screens any text for clinical-directive language
  (diagnosis/treatment/medication/etc.) that would exceed decision-support scope
  (``docs/PROJECT_SCOPE.md`` O5/O6/O7, R1). This mechanically enforces "no
  recommendation exceeds decision-support scope".
* :class:`DecisionGovernanceGate` — architecture/quality/context/risk validation
  every decision artifact passes before registry admission (risk = the scope guard).
* :class:`DecisionValidator` — integrity of a registered decision artifact +
  source immutability.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import (
    EvidenceBundle, RiskContext, PrioritizationRecord, GuidanceRecord,
    DecisionSupportRecord, DecisionVersion, artifact_id_of,
)

DECISION_KINDS = frozenset({"decision_context", "evidence_bundle", "risk_context",
                            "prioritization", "guidance", "decision_support", "decision_report"})

# Clinical-directive lexicon that is OUT OF SCOPE for decision support. Word-
# boundary matched (with optional trailing 's'); ambiguous words like "order" are
# deliberately excluded to avoid false positives.
_FORBIDDEN_TERMS = (
    "diagnosis", "diagnose", "diagnostic", "treat", "treatment", "therapy", "therapeutic",
    "prescribe", "prescription", "medication", "medicate", "dosage", "dose", "milligram",
    "administer", "contraindication",
)
_FORBIDDEN_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _FORBIDDEN_TERMS) + r")(s)?\b", re.IGNORECASE)


class DecisionValidationError(RuntimeError):
    """Raised when a mandated decision-validation check fails."""


class DecisionScopeGuard:
    """Screens text and artifacts for out-of-scope clinical-directive language."""

    def scan_text(self, text: str) -> tuple[str, ...]:
        return tuple(sorted({m.group(0).lower() for m in _FORBIDDEN_RE.finditer(text or "")}))

    def scan_artifact(self, artifact: Any) -> tuple[str, ...]:
        found: set[str] = set()
        for text in self._texts(artifact):
            found.update(self.scan_text(text))
        return tuple(sorted(found))

    def _texts(self, artifact: Any):
        if isinstance(artifact, GuidanceRecord):
            for item in artifact.items:
                yield item.message
                yield item.rationale
        elif isinstance(artifact, PrioritizationRecord):
            yield artifact.reason
        elif isinstance(artifact, DecisionSupportRecord):
            yield artifact.explanation
        elif isinstance(artifact, RiskContext):
            for c in artifact.components:
                yield c.basis


def _structural_problems(artifact: Any) -> list[str]:
    problems: list[str] = []
    if isinstance(artifact, EvidenceBundle):
        if len(artifact.items) != len(artifact.ranking):
            problems.append("evidence bundle items/ranking length mismatch")
        ranks = [it.rank for it in artifact.items]
        if ranks != list(range(1, len(ranks) + 1)):
            problems.append("evidence bundle ranks not 1..n contiguous")
        if tuple(it.evidence_id for it in artifact.items) != artifact.ranking:
            problems.append("evidence bundle item order disagrees with ranking")
        for it in artifact.items:
            if it.confidence is not None and not 0.0 <= it.confidence <= 1.0:
                problems.append(f"evidence confidence out of [0,1] for {it.evidence_id}")
    if isinstance(artifact, RiskContext):
        if not 0.0 <= artifact.aggregate <= 1.0:
            problems.append("risk aggregate out of [0,1]")
        for c in artifact.components:
            if not 0.0 <= c.value <= 1.0:
                problems.append(f"risk component {c.name} out of [0,1]")
        mean = (sum(c.value for c in artifact.components) / len(artifact.components)
                if artifact.components else 0.0)
        if abs(round(mean, 6) - artifact.aggregate) > 1e-6:
            problems.append("risk aggregate does not match component mean")
    if isinstance(artifact, PrioritizationRecord):
        if not 0.0 <= artifact.score <= 1.0:
            problems.append("prioritization score out of [0,1]")
        total = sum(f.contribution for f in artifact.factors)
        if abs(round(total, 6) - artifact.score) > 1e-6:
            problems.append("prioritization factor contributions do not sum to score")
    if isinstance(artifact, GuidanceRecord) and not artifact.items:
        problems.append("guidance record has no items")
    return problems


class DecisionGovernanceGate:
    """The architecture/quality/context/risk gate every decision artifact passes."""

    def __init__(self) -> None:
        self._guard = DecisionScopeGuard()

    def evaluate(self, *, artifact: Any, kind: str, parents: tuple = (),
                 requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        report.add("architecture_validation", kind in DECISION_KINDS,
                   f"kind={kind} is decision-producible")
        problems = _structural_problems(artifact)
        report.add("quality_validation", not problems, "; ".join(problems) or "structural checks passed")
        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")
        # Risk validation = the scope guard: no out-of-scope clinical-directive content.
        forbidden = self._guard.scan_artifact(artifact)
        report.add("risk_validation", not forbidden,
                   "within decision-support scope" if not forbidden
                   else f"out-of-scope clinical-directive language: {', '.join(forbidden)}")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise DecisionValidationError(f"decision governance gate rejected artifact: {names}")


class DecisionValidator:
    """Validates integrity of a registered decision artifact + source immutability."""

    def __init__(self) -> None:
        self._guard = DecisionScopeGuard()

    def validate(self, *, artifact: Any, kind: str, registry: Any, audit_log: Any,
                 lineage_tracker: Any, population: Optional[Any] = None,
                 baseline_digest: Optional[Mapping[str, str]] = None) -> ValidationReport:
        report = ValidationReport()
        artifact_id = artifact_id_of(artifact)
        lineage_id = getattr(artifact, "lineage_id", None)
        version = getattr(artifact, "version", "")

        report.add("identity_integrity", validate_identity(artifact_id, kind)[0],
                   f"artifact_id={artifact_id}")

        try:
            rec = registry.get(artifact_id)
            report.add("registry_integrity", rec.version == version and rec.lineage_id == lineage_id,
                       f"registered version={rec.version} artifact version={version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        try:
            heads = {e.event_hash for e in audit_log.events()}
            state = getattr(artifact, "audit_state", None)
            report.add("audit_integrity", audit_log.verify() and state in heads,
                       f"chain_verified={audit_log.verify()} audit_state_recorded={state in heads}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        try:
            chain_ok = bool(lineage_id) and lineage_tracker.verify_chain(lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        try:
            expected = DecisionVersion.compute(artifact.state_signature(), None)
            report.add("version_integrity", version == expected,
                       f"recorded={version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        problems = _structural_problems(artifact)
        report.add("content_integrity", not problems, "; ".join(problems) or "ok")

        # The defining decision-support guarantee: nothing exceeds scope.
        forbidden = self._guard.scan_artifact(artifact)
        report.add("decision_scope_integrity", not forbidden,
                   "within scope" if not forbidden else f"forbidden: {', '.join(forbidden)}")

        if population is not None and baseline_digest is not None:
            current = population.integrity_digest()
            ok = dict(current) == dict(baseline_digest)
            report.add("source_immutability", bool(ok),
                       "source digest unchanged" if ok else "source truth was modified")

        return report
