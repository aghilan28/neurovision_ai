"""Validation readiness engine (DRP6-I).

Combines the measured evidence (benchmark / reliability / calibration / evidence / registry /
audit / lineage) into a deterministic readiness score, classification, findings, and a record.

Readiness criteria (the directive): clinical validation can only be ``READY`` when benchmarks,
reliability studies, calibration studies, and evidence exist, the registry + audit + lineage
exist, validation passes, and a readiness score exists.
"""

from __future__ import annotations

from ml.provenance import hash_obj           # allowed: backend -> ml

from ..models.domain import ReadinessClass, ReadinessDimension, ReadinessRecord
from ..version import DETERMINISTIC_EPOCH

_WEIGHTS = {
    ReadinessDimension.BENCHMARK.value: 0.2,
    ReadinessDimension.RELIABILITY.value: 0.2,
    ReadinessDimension.CALIBRATION.value: 0.15,
    ReadinessDimension.EVIDENCE.value: 0.15,
    ReadinessDimension.REGISTRY.value: 0.1,
    ReadinessDimension.AUDIT.value: 0.1,
    ReadinessDimension.LINEAGE.value: 0.1,
}


class ValidationReadinessEngine:
    """Deterministic readiness assessment for a model's clinical validation evidence."""

    def assess(self, *, target_id: str, benchmark_ok: bool, reliability_ok: bool,
               calibration_ok: bool, evidence_ok: bool, registered: bool, audited: bool,
               traceable: bool, created_at: str = DETERMINISTIC_EPOCH) -> ReadinessRecord:
        dimensions = {
            ReadinessDimension.BENCHMARK.value: 1.0 if benchmark_ok else 0.0,
            ReadinessDimension.RELIABILITY.value: 1.0 if reliability_ok else 0.0,
            ReadinessDimension.CALIBRATION.value: 1.0 if calibration_ok else 0.0,
            ReadinessDimension.EVIDENCE.value: 1.0 if evidence_ok else 0.0,
            ReadinessDimension.REGISTRY.value: 1.0 if registered else 0.0,
            ReadinessDimension.AUDIT.value: 1.0 if audited else 0.0,
            ReadinessDimension.LINEAGE.value: 1.0 if traceable else 0.0,
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dimensions.items()), 6)
        findings = [d for d, v in sorted(dimensions.items()) if v < 1.0]
        all_present = (benchmark_ok and reliability_ok and calibration_ok and evidence_ok
                       and registered and audited and traceable)
        if all_present and score >= 0.999:
            classification = ReadinessClass.READY
        elif score >= 0.5:
            classification = ReadinessClass.PARTIALLY_READY
        else:
            classification = ReadinessClass.NOT_READY
        readiness_id = "validation_readiness+" + hash_obj({
            "target_id": target_id, "dimensions": dimensions, "classification": classification.value})
        return ReadinessRecord(readiness_id=readiness_id, target_id=target_id, score=score,
                               classification=classification, dimensions=dimensions,
                               findings=tuple(findings), created_at=created_at)


__all__ = ["ValidationReadinessEngine"]
