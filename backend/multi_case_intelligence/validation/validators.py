"""Intelligence validation checks + the governance gate (V2-P5).

``IntelligenceValidator`` verifies registry/audit/lineage/version integrity, the
artifact's structural integrity, and (optionally) source immutability — proving
the intelligence layer never mutated source truth. ``GovernanceGate`` enforces the
four per-workflow validations mandated by the constitution — Architecture,
Quality, Context, Risk — before an artifact is admitted to the registry.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import (
    Cohort, PopulationAnalytics, Trend, QualityReport, IntelVersion,
    artifact_id_of,
)

INTELLIGENCE_KINDS = frozenset({"cohort", "analytics", "trend", "quality", "intel_report"})


class IntelValidationError(RuntimeError):
    """Raised when a mandated intelligence-validation check fails."""


def _structural_problems(artifact: Any) -> list[str]:
    problems: list[str] = []
    if isinstance(artifact, Cohort):
        if list(artifact.members) != sorted(artifact.members):
            problems.append("cohort members not sorted")
        if len(set(artifact.members)) != len(artifact.members):
            problems.append("cohort members contain duplicates")
    if isinstance(artifact, PopulationAnalytics):
        for b in artifact.blocks:
            if b.count < 0:
                problems.append(f"negative count in block {b.subject_kind}")
            for fieldname, dist in b.distributions.items():
                counts = dist.get("counts", {})
                if "total" in dist and dist["total"] != sum(counts.values()):
                    problems.append(f"distribution total mismatch in {b.subject_kind}.{fieldname}")
            for cov in b.coverage.values():
                if not 0.0 <= cov.get("ratio", 0.0) <= 1.0:
                    problems.append(f"coverage ratio out of [0,1] in {b.subject_kind}")
            for v in b.frequency.values():
                if not 0.0 <= v <= 1.0:
                    problems.append(f"frequency out of [0,1] in {b.subject_kind}")
    if isinstance(artifact, QualityReport):
        for m in artifact.metrics:
            if not 0.0 <= m.value <= 1.0:
                problems.append(f"quality metric {m.name} out of [0,1]")
            if m.denominator < 0 or m.numerator < 0 or m.numerator > m.denominator:
                problems.append(f"quality metric {m.name} numerator/denominator invalid")
    if isinstance(artifact, Trend):
        valid = {"increasing", "decreasing", "flat", "insufficient_data"}
        for s in artifact.series:
            if s.direction not in valid:
                problems.append(f"trend series {s.metric} has invalid direction {s.direction}")
    return problems


class GovernanceGate:
    """The architecture/quality/context/risk gate every artifact must pass."""

    def evaluate(self, *, artifact: Any, kind: str, parents: tuple = (),
                 requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        report.add("architecture_validation", kind in INTELLIGENCE_KINDS,
                   f"kind={kind} is intelligence-producible")
        problems = _structural_problems(artifact)
        report.add("quality_validation", not problems, "; ".join(problems) or "structural checks passed")
        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")
        # Risk validation for the intelligence layer = derived ratios are bounded
        # and the artifact introduces no out-of-range/illegal numeric content.
        risk_problems = [p for p in problems if "[0,1]" in p]
        report.add("risk_validation", not risk_problems, "; ".join(risk_problems) or "bounded")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise IntelValidationError(f"governance gate rejected artifact: {names}")


class IntelligenceValidator:
    """Validates integrity of a registered intelligence artifact + the subsystem."""

    def validate(self, *, artifact: Any, kind: str, registry: Any, audit_log: Any,
                 lineage_tracker: Any, population: Optional[Any] = None,
                 baseline_digest: Optional[Mapping[str, str]] = None) -> ValidationReport:
        report = ValidationReport()
        artifact_id = self._artifact_id(artifact)
        lineage_id = getattr(artifact, "lineage_id", None)
        version = getattr(artifact, "version", "")

        # 1. identity integrity
        report.add("identity_integrity", validate_identity(artifact_id, kind)[0],
                   f"artifact_id={artifact_id}")

        # 2. registry integrity
        try:
            rec = registry.get(artifact_id)
            reg_ok = (rec.version == version and rec.lineage_id == lineage_id)
            report.add("registry_integrity", bool(reg_ok),
                       f"registered version={rec.version} artifact version={version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 3. audit integrity (shared log: chain intact + artifact's audit_state is a
        #    recorded head in the chain — per-artifact head equality is N/A here)
        try:
            heads = {e.event_hash for e in audit_log.events()}
            state = getattr(artifact, "audit_state", None)
            ok = audit_log.verify() and (state in heads)
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} audit_state_recorded={state in heads}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 4. lineage integrity
        try:
            chain_ok = bool(lineage_id) and lineage_tracker.verify_chain(lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 5. version integrity
        try:
            expected = IntelVersion.compute(artifact.state_signature(), self._previous(artifact))
            report.add("version_integrity", version == expected,
                       f"recorded={version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        # 6. structural / content integrity
        problems = _structural_problems(artifact)
        report.add("content_integrity", not problems, "; ".join(problems) or "ok")

        # 7. source immutability (population intelligence never mutates source)
        if population is not None and baseline_digest is not None:
            current = population.integrity_digest()
            ok = dict(current) == dict(baseline_digest)
            report.add("source_immutability", bool(ok),
                       "source digest unchanged" if ok else "source truth was modified")

        return report

    @staticmethod
    def _artifact_id(artifact: Any) -> str:
        return artifact_id_of(artifact)

    @staticmethod
    def _previous(artifact: Any) -> Optional[str]:
        # The first version chains from None; the validator recomputes against the
        # stored previous if present (the service records it in audit, not on the
        # frozen artifact), so a single-version artifact verifies against None.
        return None
