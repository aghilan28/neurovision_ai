"""``backend/dataset_integration/readiness`` — dataset readiness engine (DRP1-G).

Combines the measured evidence (completeness, validation, governance, registration,
traceability) into a deterministic readiness score, a classification
(NOT_READY / PARTIALLY_READY / READY), findings, and a record. Readiness reflects whether a
dataset is **integration-ready** (described, validated, governed, registered, traceable) —
not whether the underlying recordings are downloaded.
"""

from __future__ import annotations

from ml.provenance import hash_obj           # allowed: backend -> ml

from ..models.domain import (
    DatasetGovernanceRecord, DatasetReadinessRecord, DatasetValidationRecord, GovernanceStatus,
    ReadinessClass,
)

# dimension -> weight (sums to 1.0)
_WEIGHTS = {"completeness": 0.2, "integrity": 0.2, "validation_status": 0.2,
            "governance_status": 0.15, "registration_status": 0.15, "traceability_status": 0.1}


class ReadinessEngine:
    def assess(self, *, inventory, validation: DatasetValidationRecord,
               governance: DatasetGovernanceRecord, registered: bool, traceable: bool
               ) -> DatasetReadinessRecord:
        n_blocking = sum(1 for _c, s, p, _d in validation.findings
                         if (not p) and s in ("error", "critical"))
        gov_score = {GovernanceStatus.DOCUMENTED: 1.0, GovernanceStatus.INCOMPLETE: 0.5,
                     GovernanceStatus.MISSING: 0.0}[governance.status]
        dimensions = {
            "completeness": float(inventory.metadata_completeness),
            "integrity": 1.0 if n_blocking == 0 else max(0.0, 1.0 - 0.25 * n_blocking),
            "validation_status": 1.0 if validation.ok else 0.0,
            "governance_status": gov_score,
            "registration_status": 1.0 if registered else 0.0,
            "traceability_status": 1.0 if traceable else 0.0,
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dimensions.items()), 6)

        findings = []
        for d, v in sorted(dimensions.items()):
            if v < 1.0:
                findings.append(f"{d}={v}")

        # classification (measurable thresholds)
        if (validation.ok and registered and traceable and gov_score >= 1.0 and score >= 0.85):
            classification = ReadinessClass.READY
        elif score >= 0.5 and n_blocking == 0:
            classification = ReadinessClass.PARTIALLY_READY
        else:
            classification = ReadinessClass.NOT_READY

        readiness_id = "readiness+" + hash_obj(
            {"dimensions": dimensions, "classification": classification.value})
        return DatasetReadinessRecord(
            readiness_id=readiness_id, score=score, classification=classification,
            dimensions=dimensions, findings=tuple(findings))


__all__ = ["ReadinessEngine"]
