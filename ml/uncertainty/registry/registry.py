"""The uncertainty registry: governed, versioned uncertainty records.

Tracks the directive's mandated fields:
  Calibration Version · Conformal Version · Coverage Version · Model Version ·
  Dataset Version · Evaluation Version · Artifact Version · Lineage Version (+ id).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ...version import ARTIFACT_VERSION, LINEAGE_VERSION, DETERMINISTIC_EPOCH
from ...provenance import hash_obj, content_id
from ..version import (
    UNCERTAINTY_REGISTRY_VERSION,
    CALIBRATION_VERSION,
    CONFORMAL_VERSION,
    COVERAGE_VERSION,
    RISK_VERSION,
)


@dataclass
class UncertaintyRecord:
    """A single uncertainty registry entry."""

    uncertainty_id: str
    model_version: str
    dataset_version: str
    lineage_id: str
    calibration_version: str = CALIBRATION_VERSION
    conformal_version: str = CONFORMAL_VERSION
    coverage_version: str = COVERAGE_VERSION
    risk_version: str = RISK_VERSION
    evaluation_version: Optional[str] = None
    artifact_version: str = ARTIFACT_VERSION
    lineage_version: str = LINEAGE_VERSION
    temperature: Optional[float] = None
    target_coverage: Optional[float] = None
    observed_coverage: Optional[float] = None
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {
            "uncertainty_id": self.uncertainty_id,
            "model_version": self.model_version,
            "dataset_version": self.dataset_version,
            "evaluation_version": self.evaluation_version,
            "calibration_version": self.calibration_version,
            "conformal_version": self.conformal_version,
            "coverage_version": self.coverage_version,
            "risk_version": self.risk_version,
            "artifact_version": self.artifact_version,
            "lineage_version": self.lineage_version,
            "lineage_id": self.lineage_id,
            "temperature": self.temperature,
            "target_coverage": self.target_coverage,
            "observed_coverage": self.observed_coverage,
            "created_at": self.created_at,
        }


def make_uncertainty_id(model_version: str, dataset_version: str, evaluation_version: str | None,
                        extra: dict | None = None) -> str:
    return content_id("uncertainty", {
        "model_version": model_version,
        "dataset_version": dataset_version,
        "evaluation_version": evaluation_version,
        "extra": extra or {},
    })


class UncertaintyRegistry:
    def __init__(self) -> None:
        self._records: dict[str, UncertaintyRecord] = {}

    def register(self, record: UncertaintyRecord) -> UncertaintyRecord:
        existing = self._records.get(record.uncertainty_id)
        if existing is not None:
            if hash_obj(existing.to_dict()) != hash_obj(record.to_dict()):
                raise ValueError(
                    f"uncertainty_id {record.uncertainty_id!r} already registered with different content"
                )
            return existing
        self._records[record.uncertainty_id] = record
        return record

    def get(self, uncertainty_id: str) -> UncertaintyRecord:
        if uncertainty_id not in self._records:
            raise KeyError(f"unknown uncertainty_id {uncertainty_id!r}")
        return self._records[uncertainty_id]

    def list_records(self) -> list[str]:
        return sorted(self._records)

    def to_dict(self) -> dict:
        return {
            "uncertainty_registry_version": UNCERTAINTY_REGISTRY_VERSION,
            "n_records": len(self._records),
            "records": {uid: r.to_dict() for uid, r in sorted(self._records.items())},
        }
