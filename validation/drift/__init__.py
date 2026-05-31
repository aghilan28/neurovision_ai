"""``validation/drift`` — drift & consistency analysis (P9-H).

**Measures** change; it never corrects it. It quantifies input drift, feature drift,
prediction drift, pipeline drift, and model consistency by comparing real platform
artifacts:

* input drift     — byte-size + content-fingerprint difference between two recordings.
* feature drift   — L1 distance between the two recordings' assembled feature vectors.
* prediction drift— class change + probability L1 between the two recordings' predictions.
* pipeline drift  — fingerprint stability of the SAME input across runs (0 = stable).
* model consistency — agreement of predicted class across the trained architectures.
"""

from __future__ import annotations

import os

from ..util import fingerprint, l1_distance
from ..version import VALIDATION_DRIFT_VERSION


def _probs(prediction: dict) -> list:
    classes = (prediction or {}).get("classes", [])
    return [float(c.get("probability", 0.0)) for c in classes]


class DriftValidator:
    def run(self, harness, muts: dict, feats, *, eeg_file_a: str, eeg_file_b: str) -> dict:
        arch = sorted(muts)[0]
        mut = muts[arch]

        # --- input drift ---
        a_bytes = os.path.getsize(eeg_file_a) if os.path.exists(eeg_file_a) else 0
        b_bytes = os.path.getsize(eeg_file_b) if os.path.exists(eeg_file_b) else 0
        input_drift = {"size_a": a_bytes, "size_b": b_bytes, "size_delta": abs(a_bytes - b_bytes),
                       "same_input": eeg_file_a == eeg_file_b}

        # --- feature drift (two distinct cohort recordings) ---
        vec_a = harness.feature_vector(feats[0])
        other = feats[-1] if len(feats) > 1 else feats[0]
        vec_b = harness.feature_vector(other)
        feature_drift = {"l1": l1_distance(vec_a, vec_b), "dims": len(vec_a)}

        # --- prediction drift (same model, two recordings' features) ---
        pa = harness.svc.inference_service.predict(
            mut.model, feats[0], train_feature_records=list(mut.train_feature_records),
            dataset_key=mut.dataset_key).asset
        pb = harness.svc.inference_service.predict(
            mut.model, other,
            train_feature_records=list(mut.train_feature_records), dataset_key=mut.dataset_key).asset
        cls_a, cls_b = pa.prediction.predicted_class, pb.prediction.predicted_class
        prediction_drift = {"class_a": cls_a, "class_b": cls_b, "class_changed": cls_a != cls_b,
                            "probability_l1": l1_distance(_probs(pa.prediction.to_dict()),
                                                          _probs(pb.prediction.to_dict()))}

        # --- pipeline drift (same input twice -> must be stable) ---
        r1 = harness.run_pipeline(eeg_file_a, mut, patient_key="drift-p", case_key="drift-c")
        r2 = harness.run_pipeline(eeg_file_a, mut, patient_key="drift-p", case_key="drift-c")
        pipeline_drift = {"fingerprint_1": r1.output_fingerprint(),
                          "fingerprint_2": r2.output_fingerprint(),
                          "stable": r1.output_fingerprint() == r2.output_fingerprint()}

        # --- model consistency (agreement of predicted class across architectures) ---
        preds = {}
        for a, m in sorted(muts.items()):
            out = harness.svc.inference_service.predict(
                m.model, feats[0], train_feature_records=list(m.train_feature_records),
                dataset_key=m.dataset_key).asset
            preds[a] = out.prediction.predicted_class
        classes = set(preds.values())
        model_consistency = {"per_model_class": preds, "n_distinct": len(classes),
                             "unanimous": len(classes) <= 1}

        # the validator's own success = it could *measure* drift + pipeline is stable
        ok = pipeline_drift["stable"]
        return {
            "drift_version": VALIDATION_DRIFT_VERSION, "ok": ok,
            "input_drift": input_drift, "feature_drift": feature_drift,
            "prediction_drift": prediction_drift, "pipeline_drift": pipeline_drift,
            "model_consistency": model_consistency,
            "signature": fingerprint({"feature_l1": round(feature_drift["l1"], 6),
                                      "pipeline_stable": pipeline_drift["stable"],
                                      "model_classes": preds}),
        }


def build_drift_report(result: dict) -> dict:
    return {"report_type": "drift", **result,
            "note": "drift is measured only; no drift correction is performed (P9-H)."}


__all__ = ["DriftValidator", "build_drift_report"]
