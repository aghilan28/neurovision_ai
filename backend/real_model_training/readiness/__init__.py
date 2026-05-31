"""``backend/real_model_training/readiness`` — Serving Readiness Engine (T2-H).

Combines the evidence (training / evaluation / benchmark / validation / registry / audit /
lineage) into a deterministic score, findings, and a classification:

    NOT_READY  <  PARTIALLY_READY  <  READY_FOR_SERVING

A model is ``READY_FOR_SERVING`` only when it was trained on real data, evaluated, and
benchmarked, is registered + audited + traceable, AND its content validation passes — i.e.
there is complete, objective, reproducible evidence to put it behind a serving boundary.
Serving readiness gates on *evidence completeness + integrity*, not on an accuracy target
(the reference architectures are untuned — NR-2).
"""

from __future__ import annotations

from ml.provenance import hash_obj

from ..models.domain import ReadinessDimension, ServingReadinessClass, ServingReadinessRecord
from ..version import DETERMINISTIC_EPOCH

_WEIGHTS = {ReadinessDimension.TRAINING.value: 0.2, ReadinessDimension.EVALUATION.value: 0.2,
            ReadinessDimension.BENCHMARK.value: 0.2, ReadinessDimension.VALIDATION.value: 0.15,
            ReadinessDimension.REGISTRY.value: 0.1, ReadinessDimension.AUDIT.value: 0.05,
            ReadinessDimension.LINEAGE.value: 0.1}


class ServingReadinessEngine:
    def assess(self, *, model_id: str, training_present: bool, evaluation_present: bool,
               benchmark_present: bool, validation_ok: bool, registered: bool, audited: bool,
               traceable: bool, created_at: str = DETERMINISTIC_EPOCH) -> ServingReadinessRecord:
        dims = {
            ReadinessDimension.TRAINING.value: 1.0 if training_present else 0.0,
            ReadinessDimension.EVALUATION.value: 1.0 if evaluation_present else 0.0,
            ReadinessDimension.BENCHMARK.value: 1.0 if benchmark_present else 0.0,
            ReadinessDimension.VALIDATION.value: 1.0 if validation_ok else 0.0,
            ReadinessDimension.REGISTRY.value: 1.0 if registered else 0.0,
            ReadinessDimension.AUDIT.value: 1.0 if audited else 0.0,
            ReadinessDimension.LINEAGE.value: 1.0 if traceable else 0.0,
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dims.items()), 6)
        findings = [d for d, v in sorted(dims.items()) if v < 1.0]

        all_present = (training_present and evaluation_present and benchmark_present
                       and registered and audited and traceable)
        if all_present and validation_ok and score >= 0.999:
            classification = ServingReadinessClass.READY_FOR_SERVING
        elif score >= 0.5 and validation_ok:
            classification = ServingReadinessClass.PARTIALLY_READY
        else:
            classification = ServingReadinessClass.NOT_READY

        readiness_id = "readiness+" + hash_obj({"model_id": model_id, "dimensions": dims,
                                                "classification": classification.value})
        return ServingReadinessRecord(
            readiness_id=readiness_id, model_id=model_id, score=score,
            classification=classification, dimensions=dims, findings=tuple(findings),
            created_at=created_at)


__all__ = ["ServingReadinessEngine"]
