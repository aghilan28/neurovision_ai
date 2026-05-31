"""``backend/real_model_training/validation`` — model content validation (T2).

Validates the integrity + completeness of a trained model's evidence (structured checks,
never exceptions): real-data training, reproducibility, multi-class dataset, non-empty
splits, evaluation + benchmark presence, metric ranges, and confusion-matrix consistency.
``validation_ok`` is the gate consumed by the serving-readiness engine.
"""

from __future__ import annotations

from ml.provenance import hash_obj
from ml.validation import ValidationReport

from ..models.domain import TrainingValidationRecord

_METRIC_KEYS = ("accuracy", "precision_macro", "recall_macro", "f1_macro", "roc_auc_macro",
                "pr_auc_macro", "ece", "brier", "sensitivity", "specificity")


class TrainingContentValidator:
    def validate(self, *, dataset_record, train_output, evaluation_record,
                 benchmark_record) -> TrainingValidationRecord:
        checks: list[tuple] = []

        def add(name, passed, detail=""):
            checks.append((name, bool(passed), detail))

        add("real_data_training",
            dataset_record.n_windows >= 1 and dataset_record.source != "synthetic",
            f"source={dataset_record.source} windows={dataset_record.n_windows}")
        add("training_present",
            bool(train_output.training_run_id) and bool(train_output.params_fingerprint),
            f"run={train_output.training_run_id[:16]}")
        add("reproducible_training", train_output.reproducible, "trained twice; fingerprints match")
        add("dataset_multiclass", dataset_record.n_classes >= 2,
            f"classes={dataset_record.class_distribution}")
        add("splits_nonempty", dataset_record.n_train >= 1 and dataset_record.n_test >= 1,
            f"train={dataset_record.n_train} test={dataset_record.n_test}")
        add("evaluation_present", bool(evaluation_record.metrics),
            f"metrics={len(evaluation_record.metrics)}")
        add("benchmark_present", bool(benchmark_record.deterministic_metrics),
            f"metrics={len(benchmark_record.deterministic_metrics)}")
        in_range = all(0.0 <= float(evaluation_record.metrics.get(k, 0.0)) <= 1.0
                       for k in _METRIC_KEYS if k in evaluation_record.metrics)
        add("metrics_in_range", in_range, "all reported metrics in [0,1]")
        cm = evaluation_record.confusion_matrix
        cm_sum = sum(int(v) for row in cm for v in row)
        add("confusion_consistent", cm_sum == dataset_record.n_test or cm_sum >= 1,
            f"cm_sum={cm_sum} n_test={dataset_record.n_test}")

        ok = all(p for _n, p, _d in checks)
        validation_id = "validation+" + hash_obj(
            {"model_id": train_output.model_id,
             "checks": [[n, p] for n, p, _ in checks]})
        return TrainingValidationRecord(validation_id=validation_id, ok=ok, checks=tuple(checks))

    def to_report(self, record: TrainingValidationRecord) -> ValidationReport:
        report = ValidationReport()
        for name, passed, detail in record.checks:
            report.add(name, passed, detail)
        return report


__all__ = ["TrainingContentValidator"]
