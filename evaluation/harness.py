"""Patient-disjoint evaluation harness (the V1-P4 integration surface).

Implements the ML layer's ``EvaluationPort``: it consumes model probabilities +
true labels + patient ids and returns an ``EvaluationResult`` carrying metrics,
calibration, and an *evaluation audit* that asserts patient-disjointness (NR-3).

Boundary: ``evaluation`` imports ``ml`` (allowed: evaluation -> ml) to use the
ml-defined result contract and provenance helpers. ``ml`` never imports this.
"""

from __future__ import annotations

import numpy as np

from ml.benchmarking import EvaluationResult  # allowed edge: evaluation -> ml
from ml.provenance import hash_obj

from .version import EVALUATION_VERSION
from .metrics import compute_metrics
from .calibration_metrics import (
    expected_calibration_error,
    brier_score,
    empirical_coverage,
    average_set_size,
)


def verify_patient_disjoint(train_patients, test_patients) -> tuple[bool, list]:
    """Return ``(is_disjoint, overlap)`` for two patient collections (NR-3)."""
    tr = set(train_patients or [])
    te = set(test_patients or [])
    overlap = sorted(tr & te)
    return (len(overlap) == 0 and len(te) > 0), overlap


class PatientDisjointEvaluator:
    """Compute patient-disjoint metrics + calibration; produce an evaluation audit."""

    evaluation_version = EVALUATION_VERSION

    def evaluate(
        self,
        *,
        probabilities: np.ndarray,
        labels: np.ndarray,
        patient_ids: np.ndarray,
        class_names: tuple,
        dataset_version: str,
        split_version: str,
        train_patient_ids=None,
        n_bins: int = 10,
    ) -> EvaluationResult:
        probabilities = np.asarray(probabilities, dtype=np.float64)
        labels = np.asarray(labels, dtype=int)
        if probabilities.shape[0] != labels.shape[0]:
            raise ValueError("probabilities and labels length mismatch")
        if probabilities.shape[1] != len(class_names):
            raise ValueError("probability width must equal len(class_names)")

        test_patients = sorted({int(p) for p in np.unique(patient_ids)})
        disjoint, overlap = verify_patient_disjoint(train_patient_ids, test_patients)
        # If train patients were not supplied we cannot *prove* disjointness, so we
        # conservatively report False (NR-3: never claim patient-disjoint unproven).
        patient_disjoint = bool(disjoint) if train_patient_ids is not None else False

        overall, per_class = compute_metrics(probabilities, labels, class_names)
        ece, mce, bins = expected_calibration_error(probabilities, labels, n_bins=n_bins)
        brier = brier_score(probabilities, labels)

        evaluation_audit = {
            "evaluation_version": EVALUATION_VERSION,
            "patient_disjoint": patient_disjoint,
            "train_patients_supplied": train_patient_ids is not None,
            "train_test_overlap": overlap,
            "n_test_windows": int(labels.size),
            "n_test_patients": len(test_patients),
            "test_patients": test_patients,
            "dataset_version": dataset_version,
            "split_version": split_version,
            "assertions": [
                {"name": "probabilities_normalized",
                 "passed": bool(np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-4))},
                {"name": "labels_in_range",
                 "passed": bool(labels.min() >= 0 and labels.max() < len(class_names))},
                {"name": "patient_disjoint", "passed": patient_disjoint},
            ],
            "audit_signature": hash_obj({
                "dataset_version": dataset_version,
                "split_version": split_version,
                "test_patients": test_patients,
            }),
        }

        calibration = {
            "ece": round(ece, 6),
            "mce": round(mce, 6),
            "brier": round(brier, 6),
            "n_bins": n_bins,
            "bins": bins,
        }

        return EvaluationResult(
            evaluation_version=EVALUATION_VERSION,
            metrics=overall,
            per_class=per_class,
            evaluation_audit=evaluation_audit,
            calibration=calibration,
            coverage=None,
        )

    def measure_coverage(
        self,
        *,
        prediction_sets: np.ndarray,
        labels: np.ndarray,
        target_coverage: float,
    ) -> dict:
        """Measure empirical conformal coverage vs. its target (AP-4)."""
        observed = empirical_coverage(prediction_sets, labels)
        return {
            "evaluation_version": EVALUATION_VERSION,
            "target_coverage": float(target_coverage),
            "observed_coverage": round(observed, 6),
            "coverage_gap": round(observed - target_coverage, 6),
            "average_set_size": round(average_set_size(prediction_sets), 6),
            "meets_target": bool(observed >= target_coverage - 0.05),
        }
