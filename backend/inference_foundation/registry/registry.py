"""The inference (prediction) registry (P5-I).

No prediction asset exists outside the registry. Each entry references its model,
input feature asset, case/patient, predicted class, confidence/calibration bands,
status, audit head, and lineage node. Re-registering the *same*
``(prediction_id, version)`` with a *different* content signature is rejected (silent
overwrite forbidden). Mirrors the platform registry pattern (NR-6).
"""

from __future__ import annotations

from ..version import INFERENCE_REGISTRY_VERSION
from ..models.domain import InferenceRegistryRecord


class InferenceRegistry:
    """In-memory inference-asset registry keyed by ``prediction_id``."""

    def __init__(self) -> None:
        self._records: dict[str, InferenceRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: InferenceRegistryRecord) -> InferenceRegistryRecord:
        key = (record.prediction_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"prediction {record.prediction_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.prediction_id] = record
        return record

    def get(self, prediction_id: str) -> InferenceRegistryRecord:
        if prediction_id not in self._records:
            raise KeyError(f"prediction {prediction_id!r} not in registry")
        return self._records[prediction_id]

    def exists(self, prediction_id: str) -> bool:
        return prediction_id in self._records

    def list_predictions(self) -> list[str]:
        return sorted(self._records)

    def by_model(self, model_id: str) -> list[str]:
        return sorted(p for p, r in self._records.items() if r.model_id == model_id)

    def by_feature(self, feature_asset_id: str) -> list[str]:
        return sorted(p for p, r in self._records.items() if r.feature_asset_id == feature_asset_id)

    def by_case(self, case_id: str) -> list[str]:
        return sorted(p for p, r in self._records.items() if r.case_id == case_id)

    def by_patient(self, patient_id: str) -> list[str]:
        return sorted(p for p, r in self._records.items() if r.patient_id == patient_id)

    def to_dict(self) -> dict:
        return {
            "inference_registry_version": INFERENCE_REGISTRY_VERSION, "n_predictions": len(self._records),
            "predictions": {p: r.to_dict() for p, r in sorted(self._records.items())},
        }
