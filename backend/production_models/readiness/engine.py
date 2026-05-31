"""Production model readiness engine (DRP2-G).

Combines the measured evidence (training / evaluation / benchmark / registry / validation
/ lineage / audit) into a deterministic readiness score, a classification
(NOT_READY / PARTIALLY_READY / READY), findings, and a record.

Readiness criteria (the directive): a model can only be ``READY`` when **all** of training,
evaluation, benchmark, registry entry, audit entry, lineage entry, and a readiness score
exist **and** validation passes. The score is a weighted sum of the seven dimensions.
"""

from __future__ import annotations

from ml.provenance import hash_obj           # allowed: backend -> ml

from ..models.domain import ModelReadinessRecord, ReadinessClass, ReadinessDimension
from ..version import DETERMINISTIC_EPOCH

# dimension -> weight (sums to 1.0)
_WEIGHTS = {
    ReadinessDimension.TRAINING.value: 0.2,
    ReadinessDimension.EVALUATION.value: 0.15,
    ReadinessDimension.BENCHMARK.value: 0.2,
    ReadinessDimension.REGISTRY.value: 0.15,
    ReadinessDimension.VALIDATION.value: 0.15,
    ReadinessDimension.LINEAGE.value: 0.1,
    ReadinessDimension.AUDIT.value: 0.05,
}


class ReadinessEngine:
    """Deterministic readiness assessment for a production-candidate model."""

    def assess(self, *, model_id: str, training_present: bool, evaluation_present: bool,
               benchmark_present: bool, registered: bool, validation_ok: bool,
               traceable: bool, audited: bool,
               created_at: str = DETERMINISTIC_EPOCH) -> ModelReadinessRecord:
        dimensions = {
            ReadinessDimension.TRAINING.value: 1.0 if training_present else 0.0,
            ReadinessDimension.EVALUATION.value: 1.0 if evaluation_present else 0.0,
            ReadinessDimension.BENCHMARK.value: 1.0 if benchmark_present else 0.0,
            ReadinessDimension.REGISTRY.value: 1.0 if registered else 0.0,
            ReadinessDimension.VALIDATION.value: 1.0 if validation_ok else 0.0,
            ReadinessDimension.LINEAGE.value: 1.0 if traceable else 0.0,
            ReadinessDimension.AUDIT.value: 1.0 if audited else 0.0,
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dimensions.items()), 6)

        findings = [d for d, v in sorted(dimensions.items()) if v < 1.0]

        all_present = (training_present and evaluation_present and benchmark_present
                       and registered and traceable and audited)
        if all_present and validation_ok and score >= 0.999:
            classification = ReadinessClass.READY
        elif score >= 0.5 and validation_ok:
            classification = ReadinessClass.PARTIALLY_READY
        else:
            classification = ReadinessClass.NOT_READY

        readiness_id = "readiness+" + hash_obj({"model_id": model_id, "dimensions": dimensions,
                                                "classification": classification.value})
        return ModelReadinessRecord(
            readiness_id=readiness_id, model_id=model_id, score=score,
            classification=classification, dimensions=dimensions, findings=tuple(findings),
            created_at=created_at)


__all__ = ["ReadinessEngine"]
