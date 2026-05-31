"""Serving readiness engine (DRP3-I).

Combines the measured evidence (execution / contract / validation / registry / audit /
lineage) into a deterministic readiness score, a classification (NOT_READY /
PARTIALLY_READY / READY), findings, and a record.

Readiness criteria (the directive): a serving platform can only be ``READY`` when requests
work, responses work, the execution lifecycle works, validation passes, the registry +
audit + lineage exist, and a readiness score exists.
"""

from __future__ import annotations

from ml.provenance import hash_obj           # allowed: backend -> ml

from ..models.domain import ReadinessClass, ReadinessDimension, ServingReadinessRecord
from ..version import DETERMINISTIC_EPOCH

# dimension -> weight (sums to 1.0)
_WEIGHTS = {
    ReadinessDimension.EXECUTION.value: 0.25,
    ReadinessDimension.CONTRACT.value: 0.15,
    ReadinessDimension.VALIDATION.value: 0.2,
    ReadinessDimension.REGISTRY.value: 0.15,
    ReadinessDimension.AUDIT.value: 0.15,
    ReadinessDimension.LINEAGE.value: 0.1,
}


class ServingReadinessEngine:
    """Deterministic readiness assessment for a serving execution."""

    def assess(self, *, target_id: str, execution_ok: bool, contract_ok: bool, validation_ok: bool,
               registered: bool, audited: bool, traceable: bool,
               created_at: str = DETERMINISTIC_EPOCH) -> ServingReadinessRecord:
        dimensions = {
            ReadinessDimension.EXECUTION.value: 1.0 if execution_ok else 0.0,
            ReadinessDimension.CONTRACT.value: 1.0 if contract_ok else 0.0,
            ReadinessDimension.VALIDATION.value: 1.0 if validation_ok else 0.0,
            ReadinessDimension.REGISTRY.value: 1.0 if registered else 0.0,
            ReadinessDimension.AUDIT.value: 1.0 if audited else 0.0,
            ReadinessDimension.LINEAGE.value: 1.0 if traceable else 0.0,
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dimensions.items()), 6)
        findings = [d for d, v in sorted(dimensions.items()) if v < 1.0]

        all_present = execution_ok and contract_ok and registered and audited and traceable
        if all_present and validation_ok and score >= 0.999:
            classification = ReadinessClass.READY
        elif score >= 0.5 and validation_ok:
            classification = ReadinessClass.PARTIALLY_READY
        else:
            classification = ReadinessClass.NOT_READY

        readiness_id = "serving_readiness+" + hash_obj({
            "target_id": target_id, "dimensions": dimensions, "classification": classification.value})
        return ServingReadinessRecord(
            readiness_id=readiness_id, target_id=target_id, score=score,
            classification=classification, dimensions=dimensions, findings=tuple(findings),
            created_at=created_at)


__all__ = ["ServingReadinessEngine"]
