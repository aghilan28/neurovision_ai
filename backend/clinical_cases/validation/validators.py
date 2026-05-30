"""Case validation checks (V2-P1).

Each check is a pure assertion over the Case aggregate + its registry record, audit
log, and lineage tracker. A failing check is stop-and-remediate.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..models.domain import CaseStatus
from ..identity import validate_identity


class CaseValidationError(RuntimeError):
    """Raised when a mandated case-validation check fails."""


class CaseValidator:
    def validate(self, *, case: Any, registry: Any, audit_log: Any, lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()

        # 1. identity integrity
        id_ok, id_detail = self._identity_integrity(case)
        report.add("identity_integrity", id_ok, id_detail)

        # 2. registry integrity
        try:
            rec = registry.get(case.case_id)
            reg_ok = (rec.patient_id == case.patient_id
                      and rec.version == case.version.version
                      and rec.lineage_id == case.lineage_id
                      and set(rec.study_ids) == set(case.study_ids))
            report.add("registry_integrity", bool(reg_ok),
                       f"registered version={rec.version} case version={case.version.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 3. lifecycle integrity
        try:
            status_ok = isinstance(case.state.status, CaseStatus)
            n_state_changes = sum(1 for e in audit_log.events() if e.kind == "state_change")
            count_ok = case.state.transition_count == n_state_changes
            report.add("lifecycle_integrity", bool(status_ok and count_ok),
                       f"status={case.state.status.value} transitions={case.state.transition_count} "
                       f"audited_state_changes={n_state_changes}")
        except Exception as exc:
            report.add("lifecycle_integrity", False, f"error: {exc}")

        # 4. lineage integrity (chain from the case head reaches patient/studies/inference)
        try:
            chain_ok = bool(case.lineage_id) and lineage_tracker.verify_chain(case.lineage_id)
            studies_linked = all(
                (s.inference_lineage_id is None) or lineage_tracker.exists(s.inference_lineage_id)
                for s in case.studies)
            report.add("lineage_integrity", bool(chain_ok and studies_linked),
                       f"chain_ok={chain_ok} studies_linked={studies_linked}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 5. audit integrity (tamper-evident chain + head matches the case)
        try:
            verify_ok = audit_log.verify()
            head_ok = case.audit_head == audit_log.head
            report.add("audit_integrity", bool(verify_ok and head_ok),
                       f"chain_verified={verify_ok} head_match={head_ok}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 6. artifact integrity (each linked study carries checksummed artifact refs)
        try:
            studies_with_inf = [s for s in case.studies if s.inference_id]
            art_ok = all(s.artifact_refs and all("checksum" in ref for ref in s.artifact_refs.values())
                         for s in studies_with_inf) if studies_with_inf else True
            report.add("artifact_integrity", bool(art_ok),
                       f"studies_with_inference={len(studies_with_inf)}")
        except Exception as exc:
            report.add("artifact_integrity", False, f"error: {exc}")

        # 7. version integrity (recorded version == chained hash of state + previous)
        try:
            from ..models.domain import CaseVersion
            expected = CaseVersion.compute(case.state_signature(), case.version.previous)
            ver_ok = case.version.version == expected
            report.add("version_integrity", bool(ver_ok),
                       f"recorded={case.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report

    @staticmethod
    def _identity_integrity(case: Any) -> tuple[bool, str]:
        checks = [
            validate_identity(case.case_id, "case")[0],
            validate_identity(case.patient_id, "patient")[0],
            case.identity.patient_id == case.patient_id,
        ]
        for s in case.studies:
            checks.append(validate_identity(s.study_id, "study")[0])
            checks.append(s.case_id == case.case_id)
        ok = all(checks)
        return ok, f"case/patient/study identities valid + linked: {ok}"

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise CaseValidationError(f"case validation failed: {names}")
