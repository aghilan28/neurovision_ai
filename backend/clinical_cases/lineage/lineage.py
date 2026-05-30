"""Clinical-case lineage helpers built on ml.lineage."""

from __future__ import annotations

from typing import Mapping, Optional

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    CLINICAL_CASES_VERSION, CASE_DOMAIN_VERSION, CASE_IDENTITY_VERSION,
    CASE_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def clinical_version_bundle(**extra: object) -> dict:
    """The clinical version coordinates embedded in every clinical lineage node."""
    bundle = {
        "clinical_cases_version": CLINICAL_CASES_VERSION,
        "case_domain_version": CASE_DOMAIN_VERSION,
        "case_identity_version": CASE_IDENTITY_VERSION,
        "case_lineage_version": CASE_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_patient_lineage(patient_id: str, *, created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="patient", versions=clinical_version_bundle(),
        inputs={"patient_id": patient_id}, outputs={"patient_id": patient_id},
        parents=(), created_at=created_at)


def make_case_lineage(case_id: str, patient_id: str, patient_lineage_id: str, *,
                      created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="case", versions=clinical_version_bundle(),
        inputs={"patient_id": patient_id, "case_id": case_id},
        outputs={"case_id": case_id}, parents=(patient_lineage_id,), created_at=created_at)


def make_study_lineage(study_id: str, case_id: str, case_lineage_id: str, *,
                       inference_id: Optional[str] = None,
                       inference_lineage_id: Optional[str] = None,
                       dataset_version: Optional[str] = None,
                       created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A study lineage node; parents include the case node and (if linked) the V1
    inference lineage node — connecting the clinical graph to V1 provenance."""
    parents = [case_lineage_id]
    if inference_lineage_id:
        parents.append(inference_lineage_id)
    return make_lineage_record(
        kind="study",
        versions=clinical_version_bundle(dataset_version=dataset_version),
        inputs={"case_id": case_id, "study_id": study_id, "inference_id": inference_id},
        outputs={"study_id": study_id, "inference_lineage_id": inference_lineage_id},
        parents=tuple(parents), created_at=created_at)
