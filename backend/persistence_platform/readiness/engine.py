"""Persistence readiness engine (DRP4-K).

Combines the measured evidence (storage / registry / recovery / audit / lineage / validation)
into a deterministic readiness score, a classification (NOT_READY / PARTIALLY_READY / READY),
findings, and a record.

Readiness criteria (the directive): persistence can only be ``READY`` when storage exists,
recovery exists **and succeeds**, registry + audit + lineage persistence exist, validation
passes, and a readiness score exists.
"""

from __future__ import annotations

from ml.provenance import hash_obj           # allowed: backend -> ml

from ..models.domain import ReadinessClass, ReadinessDimension, PersistenceReadinessRecord
from ..version import DETERMINISTIC_EPOCH

# dimension -> weight (sums to 1.0)
_WEIGHTS = {
    ReadinessDimension.STORAGE.value: 0.2,
    ReadinessDimension.REGISTRY.value: 0.15,
    ReadinessDimension.RECOVERY.value: 0.25,
    ReadinessDimension.AUDIT.value: 0.15,
    ReadinessDimension.LINEAGE.value: 0.15,
    ReadinessDimension.VALIDATION.value: 0.1,
}


class PersistenceReadinessEngine:
    """Deterministic readiness assessment for a persisted-and-recovered snapshot."""

    def assess(self, *, target_id: str, storage_ok: bool, registry_ok: bool, recovery_ok: bool,
               audit_ok: bool, lineage_ok: bool, validation_ok: bool,
               created_at: str = DETERMINISTIC_EPOCH) -> PersistenceReadinessRecord:
        dimensions = {
            ReadinessDimension.STORAGE.value: 1.0 if storage_ok else 0.0,
            ReadinessDimension.REGISTRY.value: 1.0 if registry_ok else 0.0,
            ReadinessDimension.RECOVERY.value: 1.0 if recovery_ok else 0.0,
            ReadinessDimension.AUDIT.value: 1.0 if audit_ok else 0.0,
            ReadinessDimension.LINEAGE.value: 1.0 if lineage_ok else 0.0,
            ReadinessDimension.VALIDATION.value: 1.0 if validation_ok else 0.0,
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dimensions.items()), 6)
        findings = [d for d, v in sorted(dimensions.items()) if v < 1.0]

        all_present = storage_ok and registry_ok and recovery_ok and audit_ok and lineage_ok
        if all_present and validation_ok and score >= 0.999:
            classification = ReadinessClass.READY
        elif score >= 0.5 and validation_ok:
            classification = ReadinessClass.PARTIALLY_READY
        else:
            classification = ReadinessClass.NOT_READY

        readiness_id = "persistence_readiness+" + hash_obj({
            "target_id": target_id, "dimensions": dimensions, "classification": classification.value})
        return PersistenceReadinessRecord(
            readiness_id=readiness_id, target_id=target_id, score=score,
            classification=classification, dimensions=dimensions, findings=tuple(findings),
            created_at=created_at)


__all__ = ["PersistenceReadinessEngine"]
