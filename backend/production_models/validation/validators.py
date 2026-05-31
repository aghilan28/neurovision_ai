"""Production-model content validation (DRP2, build-time).

Validates the *content* of the training experiment / benchmark / evaluation / readiness
records and determinism, producing structured ``(name, passed, detail)`` results that the
service persists in the immutable ``ModelValidationRecord``. Pure functions; no exceptions.
"""

from __future__ import annotations

from ..models.domain import ProductionArchitecture


class ProductionModelContentValidator:
    """Build-time validation of the production-model records."""

    def architecture_valid(self, architecture) -> tuple[str, bool, dict]:
        ok = architecture in set(ProductionArchitecture)
        return ("architecture_valid", bool(ok), {"architecture": getattr(architecture, "value", None)})

    def training_integrity(self, experiment) -> tuple[str, bool, dict]:
        m = experiment.training_metrics
        ok = (bool(experiment.params_fingerprint) and experiment.n_params > 0
              and 0.0 <= float(m.get("train_accuracy", -1)) <= 1.0
              and len(experiment.training_history) > 0 and experiment.seed is not None)
        return ("training_integrity", bool(ok),
                {"n_params": experiment.n_params, "train_accuracy": m.get("train_accuracy")})

    def benchmark_integrity(self, benchmark) -> tuple[str, bool, dict]:
        dm = benchmark.deterministic_metrics
        required = {"accuracy", "precision_macro", "recall_macro", "f1_macro",
                    "roc_auc_macro", "pr_auc_macro", "ece", "brier"}
        ok = (required <= set(dm) and all(0.0 <= float(dm[k]) <= 1.0
                                          for k in ("accuracy", "f1_macro", "roc_auc_macro",
                                                    "pr_auc_macro")))
        return ("benchmark_integrity", bool(ok),
                {"metrics": sorted(dm), "accuracy": dm.get("accuracy")})

    def evaluation_integrity(self, evaluation, n_classes) -> tuple[str, bool, dict]:
        cm = evaluation.confusion_matrix
        shape_ok = len(cm) == n_classes and all(len(r) == n_classes for r in cm)
        ok = (shape_ok and "stability_score" in evaluation.stability_analysis
              and "bins" in evaluation.reliability_analysis)
        return ("evaluation_integrity", bool(ok),
                {"confusion_shape": [len(cm), len(cm[0]) if cm else 0]})

    def determinism_integrity(self, reproducible, detail) -> tuple[str, bool, dict]:
        return ("determinism_integrity", bool(reproducible), dict(detail))

    def content_checks(self, *, architecture, experiment, benchmark, evaluation, n_classes,
                       reproducible, determinism_detail) -> list[tuple]:
        return [
            self.architecture_valid(architecture),
            self.training_integrity(experiment),
            self.benchmark_integrity(benchmark),
            self.evaluation_integrity(evaluation, n_classes),
            self.determinism_integrity(reproducible, determinism_detail),
        ]


__all__ = ["ProductionModelContentValidator"]
