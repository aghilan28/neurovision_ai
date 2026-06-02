"""``backend/dataset_acquisition/readiness`` — Dataset Readiness Engine (T1-G).

Combines the measured evidence (acquisition / validation / label / metadata / registry /
training dimensions) into a deterministic readiness score, findings, and a classification:

    NOT_READY  <  PARTIALLY_READY  <  READY_FOR_TRAINING

A dataset is ``READY_FOR_TRAINING`` only when it physically exists + verifies, its structure
validates, its **real** labels are complete (coverage 1.0), consistent and multi-class, its
metadata is complete, it is registered + traceable, and its channels/sampling are
train-consistent — i.e. it can be used for model training **without synthetic labels**.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import (
    AvailabilityState, TrainingReadinessClass, TrainingReadinessRecord,
)

# dimension -> weight (sums to 1.0)
_WEIGHTS = {"acquisition": 0.15, "validation": 0.2, "labels": 0.25, "metadata": 0.15,
            "registry": 0.1, "training": 0.15}

_ACQ_SCORE = {
    AvailabilityState.READY: 1.0, AvailabilityState.VERIFIED: 1.0,
    AvailabilityState.DOWNLOADED: 0.6, AvailabilityState.PARTIALLY_DOWNLOADED: 0.3,
    AvailabilityState.DOWNLOADING: 0.1, AvailabilityState.CORRUPTED: 0.0,
    AvailabilityState.UNAVAILABLE: 0.0,
}


class TrainingReadinessEngine:
    def assess(self, *, availability, validation, label_verification, inventory,
               metadata_fraction: float, registered: bool, traceable: bool
               ) -> TrainingReadinessRecord:
        acq = _ACQ_SCORE.get(availability.state, 0.0)

        val = (1.0 if validation.ok
               else max(0.0, 1.0 - 0.25 * validation.n_blocking_failed))

        coverage = label_verification.coverage
        multiclass = label_verification.n_classes >= 2
        labels_dim = coverage * (1.0 if label_verification.consistent else 0.5) \
            * (1.0 if multiclass else 0.5)

        meta = max(0.0, min(1.0, float(metadata_fraction)))

        reg = 1.0 if registered else 0.0

        channel_consistent = len(inventory.n_channels_distribution) == 1
        sampling_consistent = len(inventory.sampling_frequencies) == 1
        train_usable = (coverage >= 1.0 and multiclass and inventory.n_recordings >= 1)
        training_dim = (0.34 * (1.0 if channel_consistent else 0.0)
                        + 0.33 * (1.0 if sampling_consistent else 0.0)
                        + 0.33 * (1.0 if train_usable else 0.0))

        dimensions = {
            "acquisition": round(acq, 6), "validation": round(val, 6),
            "labels": round(labels_dim, 6), "metadata": round(meta, 6),
            "registry": round(reg, 6), "training": round(training_dim, 6),
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dimensions.items()), 6)

        findings = [f"{d}={v}" for d, v in sorted(dimensions.items()) if v < 1.0]

        verified = availability.state in (AvailabilityState.VERIFIED, AvailabilityState.READY)
        fully_train_ready = (validation.ok and verified and coverage >= 1.0
                             and label_verification.consistent and multiclass
                             and meta >= 1.0 and registered and traceable
                             and channel_consistent and sampling_consistent and score >= 0.9)
        if fully_train_ready:
            classification = TrainingReadinessClass.READY_FOR_TRAINING
        elif score >= 0.5 and validation.n_blocking_failed == 0:
            classification = TrainingReadinessClass.PARTIALLY_READY
        else:
            classification = TrainingReadinessClass.NOT_READY

        readiness_id = "training_readiness+" + hash_obj(
            {"dimensions": dimensions, "classification": classification.value})
        return TrainingReadinessRecord(
            readiness_id=readiness_id, score=score, classification=classification,
            dimensions=dimensions, findings=tuple(findings))


__all__ = ["TrainingReadinessEngine"]
