"""Finding validation checks (V2-P3)."""

from __future__ import annotations

from typing import Any, Mapping

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..models.domain import FindingStatus, FindingVersion
from ..identity import validate_identity
from ..evidence import VALID_EVIDENCE_TYPES


class FindingValidationError(RuntimeError):
    """Raised when a mandated finding-validation check fails."""


class FindingValidator:
    def validate(self, *, finding: Any, registry: Any, audit_log: Any, lineage_tracker: Any,
                 interpretations: Mapping[str, Any]) -> ValidationReport:
        report = ValidationReport()

        # 1. evidence integrity (a finding must never exist without evidence)
        ev_ok, ev_detail = self._evidence_integrity(finding, lineage_tracker)
        report.add("evidence_integrity", ev_ok, ev_detail)

        # 2. interpretation integrity (separate entities; evidence-grounded)
        int_ok, int_detail = self._interpretation_integrity(finding, interpretations)
        report.add("interpretation_integrity", int_ok, int_detail)

        # 3. audit integrity
        try:
            ok = audit_log.verify() and finding.audit_head == audit_log.head
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} head_match={finding.audit_head == audit_log.head}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 4. lineage integrity
        try:
            chain_ok = bool(finding.lineage_id) and lineage_tracker.verify_chain(finding.lineage_id)
            review_ok = (finding.review_lineage_id is None) or lineage_tracker.exists(finding.review_lineage_id)
            ev_nodes_ok = all((e.lineage_id is None) or lineage_tracker.exists(e.lineage_id)
                              for e in finding.evidence)
            report.add("lineage_integrity", bool(chain_ok and review_ok and ev_nodes_ok),
                       f"chain_ok={chain_ok} review_linked={review_ok} evidence_nodes={ev_nodes_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 5. registry integrity
        try:
            rec = registry.get(finding.finding_id)
            reg_ok = (rec.version == finding.version.version and rec.lineage_id == finding.lineage_id
                      and set(rec.evidence_ids) == set(finding.evidence_ids)
                      and set(rec.interpretation_ids) == set(finding.interpretation_ids))
            report.add("registry_integrity", bool(reg_ok),
                       f"registered version={rec.version} finding version={finding.version.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 6. version integrity
        try:
            expected = FindingVersion.compute(finding.state_signature(), finding.version.previous)
            report.add("version_integrity", finding.version.version == expected,
                       f"recorded={finding.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        # 7. lifecycle integrity
        try:
            status_ok = isinstance(finding.status, FindingStatus)
            id_ok = validate_identity(finding.finding_id, "finding")[0]
            n_state_changes = sum(1 for e in audit_log.events() if e.kind == "state_change")
            count_ok = finding.transition_count == n_state_changes
            report.add("lifecycle_integrity", bool(status_ok and id_ok and count_ok),
                       f"status={finding.status.value} transitions={finding.transition_count} "
                       f"audited={n_state_changes}")
        except Exception as exc:
            report.add("lifecycle_integrity", False, f"error: {exc}")

        return report

    @staticmethod
    def _evidence_integrity(finding: Any, lineage_tracker: Any) -> tuple[bool, str]:
        if not finding.evidence:
            return False, "finding has no evidence (forbidden)"
        for e in finding.evidence:
            if e.evidence_type not in VALID_EVIDENCE_TYPES:
                return False, f"evidence {e.evidence_id} has invalid type {e.evidence_type}"
            if not e.evidence_source or not e.evidence_version:
                return False, f"evidence {e.evidence_id} missing source/version"
            if e.finding_id != finding.finding_id:
                return False, f"evidence {e.evidence_id} not linked to this finding"
        return True, f"{len(finding.evidence)} evidence item(s) valid"

    @staticmethod
    def _interpretation_integrity(finding: Any, interpretations: Mapping[str, Any]) -> tuple[bool, str]:
        for iid in finding.interpretation_ids:
            interp = interpretations.get(iid)
            if interp is None:
                return False, f"interpretation {iid} missing from store"
            if interp.finding_id != finding.finding_id:
                return False, f"interpretation {iid} not linked to this finding"
            if not set(interp.supporting_evidence).issubset(set(finding.evidence_ids)):
                return False, f"interpretation {iid} cites evidence not on this finding"
        return True, f"{len(finding.interpretation_ids)} interpretation(s) consistent"

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise FindingValidationError(f"finding validation failed: {names}")
