"""Clinical reliability program (DRP6-E).

Evaluates repeatability, reproducibility, cross-run stability, cross-dataset stability, and
failure modes for one model, producing a deterministic :class:`ReliabilityRecord`. Built from
already-computed deterministic signals (DRP-2 benchmark signatures + the DRP-2 evaluation's
stability analysis) plus a structured failure-mode probe set — no retraining beyond the
reused DRP-2 development passes.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import ReliabilityRecord
from ..version import DETERMINISTIC_EPOCH


def build_reliability(*, model_id: str, base_outcome, repeat_outcome, cross_dataset_outcome,
                      failure_modes: tuple,
                      created_at: str = DETERMINISTIC_EPOCH) -> ReliabilityRecord:
    # repeatability: re-developing the same architecture reproduces the same benchmark signature
    repeatable = (base_outcome.benchmark.metrics_signature()
                  == repeat_outcome.benchmark.metrics_signature()
                  and base_outcome.model.model_id == repeat_outcome.model.model_id)
    # reproducibility: the training experiment self-verified bit-for-bit (DRP-2)
    reproducible = bool(base_outcome.experiment.reproducible)
    # cross-run stability: predictions stable under the DRP-2 fixed perturbation set
    cross_run_stability = float(base_outcome.evaluation.stability_analysis.get("stability_score", 0.0))
    # cross-dataset stability: 1 - |accuracy delta| across an alternate dataset split
    a0 = float(base_outcome.benchmark.deterministic_metrics.get("accuracy", 0.0))
    a1 = float(cross_dataset_outcome.benchmark.deterministic_metrics.get("accuracy", 0.0))
    cross_dataset_stability = max(0.0, 1.0 - abs(a0 - a1))
    handled = sum(1 for f in failure_modes if f.get("handled"))
    fm_score = handled / len(failure_modes) if failure_modes else 1.0

    reliability_score = round(
        0.3 * (1.0 if repeatable else 0.0) + 0.2 * (1.0 if reproducible else 0.0)
        + 0.2 * cross_run_stability + 0.2 * cross_dataset_stability + 0.1 * fm_score, 6)

    reliability_key = hash_obj({"model_id": model_id, "repeatable": repeatable,
                                "reproducible": reproducible,
                                "cross_run": round(cross_run_stability, 9),
                                "cross_dataset": round(cross_dataset_stability, 9),
                                "failure_modes": [dict(sorted(f.items())) for f in failure_modes]})
    return ReliabilityRecord(
        reliability_id=mint_identity("validation_reliability", {
            "model_id": model_id, "reliability_key": reliability_key}).id,
        model_id=model_id, repeatable=repeatable, reproducible=reproducible,
        cross_run_stability=cross_run_stability, cross_dataset_stability=cross_dataset_stability,
        failure_modes=tuple(failure_modes), reliability_score=reliability_score)


__all__ = ["build_reliability"]
