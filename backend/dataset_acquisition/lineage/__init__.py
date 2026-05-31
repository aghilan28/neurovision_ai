"""``backend/dataset_acquisition/lineage`` — real-dataset lineage (T1-H).

No parallel lineage system: every node is recorded in the same
``ml.lineage.LineageTracker`` as the rest of the platform. The required chain is

    Dataset Source -> Dataset -> Patient -> Recording -> Label -> Registry

so a single ``verify_chain`` from the registry node reaches the source (and, when the
dataset is later attached to patients/cases, the wider patient lineage). Deterministic
(content-addressed ids; no wall-clock in the id).
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageTracker, LineageRecord  # allowed: backend -> ml

from ..version import (
    ACQUISITION_DOMAIN_VERSION, ACQUISITION_LINEAGE_VERSION, DATASET_ACQUISITION_VERSION,
    DETERMINISTIC_EPOCH,
)


def version_bundle(**extra) -> dict:
    bundle = {"dataset_acquisition_version": DATASET_ACQUISITION_VERSION,
              "acquisition_domain_version": ACQUISITION_DOMAIN_VERSION,
              "acquisition_lineage_version": ACQUISITION_LINEAGE_VERSION}
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_source_lineage(source_id: str, *, source: str,
                        created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="dataset_source", versions=version_bundle(),
                               inputs={"source": source}, outputs={"source_id": source_id},
                               parents=(), created_at=created_at)


def make_dataset_lineage(dataset_id: str, source_id: str, source_node: str, *,
                         content_fingerprint: str,
                         created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="real_dataset", versions=version_bundle(),
        inputs={"source_id": source_id, "content_fingerprint": content_fingerprint},
        outputs={"dataset_id": dataset_id}, parents=(source_node,), created_at=created_at)


def make_patient_lineage(patient_id: str, dataset_id: str, dataset_node: str, *,
                         patient_key: str, created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="dataset_patient", versions=version_bundle(),
        inputs={"dataset_id": dataset_id, "patient_key": patient_key},
        outputs={"patient_id": patient_id}, parents=(dataset_node,), created_at=created_at)


def make_recording_lineage(recording_id: str, patient_id: str, patient_node: str, *,
                           relative_path: str, checksum: str,
                           created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="dataset_recording", versions=version_bundle(),
        inputs={"patient_id": patient_id, "relative_path": relative_path, "checksum": checksum},
        outputs={"recording_id": recording_id}, parents=(patient_node,), created_at=created_at)


def make_label_lineage(label_id: str, recording_id: str, recording_node: str, *,
                       scheme: str, value: str,
                       created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="dataset_label", versions=version_bundle(),
        inputs={"recording_id": recording_id, "scheme": scheme, "value": value},
        outputs={"label_id": label_id}, parents=(recording_node,), created_at=created_at)


def make_registry_lineage(dataset_id: str, label_nodes: tuple, *,
                          n_recordings: int, n_labels: int,
                          created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="dataset_registry", versions=version_bundle(),
        inputs={"dataset_id": dataset_id, "n_recordings": n_recordings, "n_labels": n_labels},
        outputs={"registry_for": dataset_id}, parents=tuple(label_nodes), created_at=created_at)


__all__ = [
    "version_bundle", "make_source_lineage", "make_dataset_lineage", "make_patient_lineage",
    "make_recording_lineage", "make_label_lineage", "make_registry_lineage",
    "LineageTracker", "LineageRecord", "make_lineage_record",
]
