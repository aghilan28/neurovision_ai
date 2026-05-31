"""``backend/application_platform/validation`` — application integrity validation (T3).

Validates the integrity + completeness of a completed user workflow (structured checks,
never exceptions): real upload validated, prediction produced, workflow completed, report
generated, registry orphan-free, audit verified, lineage traceable. ``ok`` feeds readiness.
"""

from __future__ import annotations

from ml.provenance import hash_obj
from ml.validation import ValidationReport

from ..models.domain import ValidationRecord


class ApplicationIntegrityValidator:
    def validate(self, *, upload, analysis, prediction_result, report_record, workflow,
                 registry, audit_log, lineage_tracker) -> ValidationRecord:
        checks: list[tuple] = []

        def add(name, ok, detail=""):
            checks.append((name, bool(ok), detail))

        add("upload_validated", upload is not None and upload.status.value == "validated",
            f"status={getattr(upload, 'status', None)}")
        add("prediction_produced", prediction_result is not None
            and bool(prediction_result.predicted_label),
            f"label={getattr(prediction_result, 'predicted_label', None)}")
        add("workflow_completed", workflow is not None and workflow.status.value == "completed",
            f"status={getattr(workflow, 'status', None)}")
        add("report_generated", report_record is not None
            and bool(report_record.available_formats),
            f"formats={getattr(report_record, 'available_formats', ())}")
        add("registry_no_orphans", registry.orphans() == [],
            f"orphans={len(registry.orphans())}")
        add("audit_verified", audit_log.verify(), f"events={len(audit_log)}")
        traceable = bool(report_record and report_record.lineage_id
                         and lineage_tracker.verify_chain(report_record.lineage_id))
        add("lineage_traceable", traceable, "report chain verifies to recording + model")

        ok = all(p for _n, p, _d in checks)
        validation_id = "app_validation+" + hash_obj(
            {"workflow": getattr(workflow, "workflow_id", ""),
             "checks": [[n, p] for n, p, _ in checks]})
        return ValidationRecord(validation_id=validation_id, ok=ok, checks=tuple(checks))

    def to_report(self, record: ValidationRecord) -> ValidationReport:
        report = ValidationReport()
        for name, passed, detail in record.checks:
            report.add(name, passed, detail)
        return report


__all__ = ["ApplicationIntegrityValidator"]
