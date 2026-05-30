"""Model-foundation *integrity* validation (P4-K, post-build).

Reuses ``ml.validation.ValidationReport`` to produce the full nine mandated checks
over a finalized, registered model: the five content checks (dataset / training /
evaluation / model / determinism — re-affirmed from the records) plus the four
structural checks (registry, audit, lineage, version). The result shape matches the
rest of the platform (NR-6).
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import ModelVersion


class ModelIntegrityValidator:
    """Runs the mandated model-foundation integrity checks."""

    def validate(self, *, model: Any, dataset_record: Any, training_run: Any, evaluation: Any,
                 dataset_registry: Any, model_registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()

        # --- content checks re-affirmed from the immutable records ---
        report.add("dataset_integrity",
                   dataset_record.n_features == model.metadata.n_features
                   and (dataset_record.split is None or dataset_record.split.patient_disjoint),
                   f"n_features={dataset_record.n_features} patient_disjoint="
                   f"{dataset_record.split.patient_disjoint if dataset_record.split else None}")
        report.add("training_integrity",
                   bool(training_run.params_fingerprint) and training_run.n_params > 0,
                   f"n_params={training_run.n_params}")
        n_classes = model.metadata.n_classes
        cm = evaluation.confusion_matrix
        report.add("evaluation_integrity",
                   len(cm) == n_classes and all(len(r) == n_classes for r in cm),
                   f"confusion={len(cm)}x{len(cm[0]) if cm else 0}")
        report.add("model_integrity",
                   model.params_fingerprint == training_run.params_fingerprint
                   and model.metadata.n_params == training_run.n_params,
                   f"params_fingerprint match={model.params_fingerprint == training_run.params_fingerprint}")
        det = next((c for c in model.validation.checks if c[0] == "determinism_integrity"), None)
        report.add("determinism_integrity", bool(det[1]) if det else False,
                   "re-training reproduces identical parameter fingerprints")

        # --- registry integrity ---
        try:
            rec = model_registry.get(model.model_id)
            ds_ok = dataset_registry.exists(model.dataset_id)
            ok = (rec.version == model.version.version and rec.lineage_id == model.lineage_id
                  and rec.status == model.status and rec.dataset_id == model.dataset_id and ds_ok)
            report.add("registry_integrity", bool(ok),
                       f"model registered={rec.version} dataset_registered={ds_ok}")
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
            chain_ok = bool(model.lineage_id) and lineage_tracker.verify_chain(model.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(model.lineage_id)}
                     if model.lineage_id else set())
            reaches = {"patient", "case", "eeg", "processed_eeg", "feature",
                       "dataset", "training_run", "model"} <= kinds
            ids_ok = (validate_identity(model.model_id, "model")[0]
                      and validate_identity(model.training_run_id, "training_run")[0]
                      and validate_identity(model.dataset_id, "dataset")[0])
            report.add("lineage_integrity", bool(chain_ok and reaches and ids_ok),
                       f"chain_ok={chain_ok} kinds={sorted(kinds)}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # --- version integrity ---
        try:
            expected = ModelVersion.compute(model.state_signature(), model.version.previous)
            report.add("version_integrity", model.version.version == expected,
                       f"recorded={model.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report
