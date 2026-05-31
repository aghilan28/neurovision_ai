"""``backend/real_model_training/evaluation`` — Model Evaluation (T2-E).

Evaluates a trained model on the **real** dataset by REUSING the model-foundation evaluator
(accuracy / precision / recall / F1 / confusion / calibration) and the production extended
evaluation (confusion / calibration / error / stability / reliability), and additionally
computes **sensitivity + specificity** from the confusion matrix. Real EEG data only.
"""

from __future__ import annotations

import numpy as np

from backend.model_foundation import evaluate as foundation_evaluate
from backend.model_foundation.models.domain import SplitName
from backend.production_models.evaluation import build_model_evaluation

from ..identity import mint
from ..models.domain import EvaluationSummaryRecord
from ..version import DETERMINISTIC_EPOCH


def _sensitivity_specificity(confusion) -> tuple:
    """Binary sensitivity (recall of seizure=class 1) + specificity (recall of class 0)."""
    cm = np.asarray(confusion, dtype=float)
    if cm.shape != (2, 2):
        # multi-class fallback: macro one-vs-rest sensitivity; specificity from complement
        total = cm.sum()
        sens, spec = [], []
        for c in range(cm.shape[0]):
            tp = cm[c, c]
            fn = cm[c, :].sum() - tp
            fp = cm[:, c].sum() - tp
            tn = total - tp - fn - fp
            sens.append(tp / (tp + fn) if (tp + fn) else 0.0)
            spec.append(tn / (tn + fp) if (tn + fp) else 0.0)
        return float(np.mean(sens)), float(np.mean(spec))
    tn, fp, fn, tp = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
    sens = float(tp / (tp + fn)) if (tp + fn) else 0.0
    spec = float(tn / (tn + fp)) if (tn + fp) else 0.0
    return sens, spec


def evaluate_model(model, bundle, *, model_id: str, training_run_id: str, n_classes: int,
                   benchmark_metrics: dict, created_at: str = DETERMINISTIC_EPOCH):
    """Return ``(EvaluationSummaryRecord, base_evaluation_id, model_evaluation_id)``."""
    base = foundation_evaluate(model, bundle, training_run_id=training_run_id,
                               n_classes=n_classes, split=SplitName.TEST)
    model_eval = build_model_evaluation(model, bundle, model_id=model_id,
                                        evaluation_id=base.evaluation_id, n_classes=n_classes,
                                        created_at=created_at)
    sensitivity, specificity = _sensitivity_specificity(model_eval.confusion_matrix)

    bm = dict(benchmark_metrics)
    metrics = {
        "accuracy": bm.get("accuracy", float(base.metrics.get("accuracy", 0.0))),
        "precision_macro": bm.get("precision_macro", float(base.metrics.get("precision_macro", 0.0))),
        "recall_macro": bm.get("recall_macro", float(base.metrics.get("recall_macro", 0.0))),
        "f1_macro": bm.get("f1_macro", float(base.metrics.get("f1_macro", 0.0))),
        "roc_auc_macro": bm.get("roc_auc_macro", 0.0), "pr_auc_macro": bm.get("pr_auc_macro", 0.0),
        "ece": bm.get("ece", float(model_eval.calibration_analysis.get("ece", 0.0))),
        "brier": bm.get("brier", float(model_eval.calibration_analysis.get("brier", 0.0))),
        "sensitivity": sensitivity, "specificity": specificity,
    }
    evaluation_id = mint("model_evaluation_summary", {
        "model_id": model_id, "model_evaluation_id": model_eval.model_evaluation_id,
        "metrics": {k: round(float(v), 9) for k, v in sorted(metrics.items())}})
    record = EvaluationSummaryRecord(
        evaluation_id=evaluation_id, model_id=model_id, dataset_id=bundle.record.dataset_id,
        split=model_eval.split, metrics=metrics, confusion_matrix=model_eval.confusion_matrix,
        calibration=dict(model_eval.calibration_analysis),
        reliability=dict(model_eval.reliability_analysis),
        base_evaluation_id=base.evaluation_id, model_evaluation_id=model_eval.model_evaluation_id,
        created_at=created_at)
    return record, base.evaluation_id, model_eval.model_evaluation_id


__all__ = ["evaluate_model"]
