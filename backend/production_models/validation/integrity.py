"""Production-model *integrity* validation (DRP2, post-build).

Reuses ``ml.validation.ValidationReport`` to produce the mandated checks over a finalized,
registered production model: training / evaluation / benchmark / registry / audit /
lineage / readiness / version / traceability. The result shape matches the rest of the
platform (NR-6).
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import ModelVersion


# the lineage kinds that prove a production model's readiness traces to the patient
_REQUIRED_CHAIN_KINDS = {
    "patient", "case", "eeg", "processed_eeg", "feature", "dataset", "training_run",
    "training_experiment", "model", "benchmark", "readiness_assessment",
}


class ProductionModelIntegrityValidator:
    """Runs the mandated production-model integrity checks."""

    def validate(self, *, model: Any, experiment: Any, benchmark: Any, evaluation: Any,
                 readiness: Any, dataset_registry: Any, model_registry: Any,
                 production_registry: Any, audit_log: Any, lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()

        # --- training integrity ---
        report.add("training_integrity",
                   bool(experiment.params_fingerprint) and experiment.n_params > 0
                   and experiment.reproducible,
                   f"n_params={experiment.n_params} reproducible={experiment.reproducible}")

        # --- evaluation integrity ---
        cm = evaluation.confusion_matrix
        report.add("evaluation_integrity",
                   len(cm) > 0 and all(len(r) == len(cm) for r in cm)
                   and "stability_score" in evaluation.stability_analysis,
                   f"confusion={len(cm)}x{len(cm[0]) if cm else 0}")

        # --- benchmark integrity ---
        dm = benchmark.deterministic_metrics
        report.add("benchmark_integrity",
                   {"accuracy", "f1_macro", "roc_auc_macro", "pr_auc_macro", "ece", "brier"} <= set(dm)
                   and benchmark.benchmark_id == model.benchmark_id,
                   f"benchmark_id_match={benchmark.benchmark_id == model.benchmark_id}")

        # --- registry integrity (production registry + shared dataset/model registries) ---
        try:
            rec = production_registry.get_model(model.model_id)
            ds_ok = dataset_registry.exists(model.dataset_id)
            base_ok = model_registry.exists(model.model_id)  # base model in shared ModelRegistry
            ok = (rec.version == model.version.version and rec.lineage_id == model.lineage_id
                  and rec.benchmark_id == model.benchmark_id and ds_ok and base_ok
                  and production_registry.orphans() == [])
            report.add("registry_integrity", bool(ok),
                       f"production_registered={rec.version} dataset_registered={ds_ok} "
                       f"base_model_registered={base_ok} orphans={len(production_registry.orphans())}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("registry_integrity", False, f"error: {exc}")

        # --- audit integrity ---
        try:
            ok = audit_log.verify() and model.audit_head == audit_log.head
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} head_match={model.audit_head == audit_log.head}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # --- lineage integrity (chain reaches the patient root) ---
        try:
            chain_ok = bool(model.lineage_id) and lineage_tracker.verify_chain(readiness.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(readiness.lineage_id)}
                     if readiness.lineage_id else set())
            reaches = _REQUIRED_CHAIN_KINDS <= kinds
            ids_ok = (validate_identity(model.model_id, "production_model")[0]
                      and validate_identity(model.training_experiment_id, "training_experiment")[0]
                      and validate_identity(model.benchmark_id, "benchmark")[0])
            report.add("lineage_integrity", bool(chain_ok and reaches and ids_ok),
                       f"chain_ok={chain_ok} reaches_patient={reaches}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # --- readiness integrity ---
        report.add("readiness_integrity",
                   readiness.readiness_id == model.readiness_id
                   and 0.0 <= readiness.score <= 1.0 and bool(readiness.dimensions),
                   f"classification={readiness.classification.value} score={readiness.score}")

        # --- version integrity ---
        try:
            expected = ModelVersion.compute(model.state_signature(), model.version.previous)
            report.add("version_integrity", model.version.version == expected,
                       f"recorded={model.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        # --- traceability integrity (explicit end-to-end check) ---
        report.add("traceability_integrity",
                   bool(readiness.lineage_id) and lineage_tracker.verify_chain(readiness.lineage_id),
                   "Dataset -> Feature -> Training Run -> Experiment -> Model -> Benchmark -> Readiness")

        return report


__all__ = ["ProductionModelIntegrityValidator"]
