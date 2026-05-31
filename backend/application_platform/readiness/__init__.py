"""``backend/application_platform/readiness`` — Application Readiness Engine (T3-I).

Combines the product evidence (upload / prediction / workflow / report / registry / audit /
lineage) into a deterministic score, findings, and a classification:

    NOT_READY  <  PARTIALLY_READY  <  READY_FOR_USERS

The platform is ``READY_FOR_USERS`` only when a real EEG can be uploaded + validated, a
prediction generated, the workflow completed, a report produced, and all of it registered +
audited + traceable — i.e. a complete, reproducible user workflow with objective evidence.
"""

from __future__ import annotations

from ml.provenance import hash_obj

from ..models.domain import ApplicationReadinessClass, ReadinessDimension, ReadinessRecord
from ..version import DETERMINISTIC_EPOCH

_WEIGHTS = {ReadinessDimension.UPLOAD.value: 0.2, ReadinessDimension.PREDICTION.value: 0.25,
            ReadinessDimension.WORKFLOW.value: 0.2, ReadinessDimension.REPORT.value: 0.1,
            ReadinessDimension.REGISTRY.value: 0.1, ReadinessDimension.AUDIT.value: 0.05,
            ReadinessDimension.LINEAGE.value: 0.1}


class ApplicationReadinessEngine:
    def assess(self, *, subject: str, upload_ok: bool, prediction_ok: bool, workflow_ok: bool,
               report_ok: bool, registered: bool, audited: bool, traceable: bool,
               created_at: str = DETERMINISTIC_EPOCH) -> ReadinessRecord:
        dims = {
            ReadinessDimension.UPLOAD.value: 1.0 if upload_ok else 0.0,
            ReadinessDimension.PREDICTION.value: 1.0 if prediction_ok else 0.0,
            ReadinessDimension.WORKFLOW.value: 1.0 if workflow_ok else 0.0,
            ReadinessDimension.REPORT.value: 1.0 if report_ok else 0.0,
            ReadinessDimension.REGISTRY.value: 1.0 if registered else 0.0,
            ReadinessDimension.AUDIT.value: 1.0 if audited else 0.0,
            ReadinessDimension.LINEAGE.value: 1.0 if traceable else 0.0,
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dims.items()), 6)
        findings = [d for d, v in sorted(dims.items()) if v < 1.0]

        all_present = (upload_ok and prediction_ok and workflow_ok and report_ok
                       and registered and audited and traceable)
        if all_present and score >= 0.999:
            classification = ApplicationReadinessClass.READY_FOR_USERS
        elif score >= 0.5:
            classification = ApplicationReadinessClass.PARTIALLY_READY
        else:
            classification = ApplicationReadinessClass.NOT_READY

        readiness_id = "app_readiness+" + hash_obj({"subject": subject, "dimensions": dims,
                                                    "classification": classification.value})
        return ReadinessRecord(readiness_id=readiness_id, subject=subject, score=score,
                               classification=classification, dimensions=dims,
                               findings=tuple(findings), created_at=created_at)


__all__ = ["ApplicationReadinessEngine"]
