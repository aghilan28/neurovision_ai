"""Clinical-validation lineage helpers on the shared ``ml.lineage`` machinery (DRP6-H).

No parallel lineage system: the validation nodes are recorded in the *same*
``ml.lineage.LineageTracker`` as every upstream node. The benchmark node parents the
**production model** node (which already chains model -> training -> dataset -> feature ->
patient), so the chain is

    Dataset -> Model -> Benchmark -> Evaluation -> Evidence -> Readiness Assessment

and a single ``verify_chain`` from a readiness node reaches the patient.
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    CLINICAL_VALIDATION_VERSION, CLINICAL_DOMAIN_VERSION, CLINICAL_IDENTITY_VERSION,
    CLINICAL_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)

__all__ = [
    "make_benchmark_lineage", "make_evaluation_lineage", "make_evidence_lineage",
    "make_readiness_lineage", "clinical_version_bundle",
]


def clinical_version_bundle(**extra: object) -> dict:
    bundle = {
        "clinical_validation_version": CLINICAL_VALIDATION_VERSION,
        "clinical_domain_version": CLINICAL_DOMAIN_VERSION,
        "clinical_identity_version": CLINICAL_IDENTITY_VERSION,
        "clinical_lineage_version": CLINICAL_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_benchmark_lineage(benchmark_id: str, model_lineage_id: str, *, dataset_label: str,
                           created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="validation_benchmark", versions=clinical_version_bundle(),
        inputs={"model_id": model_lineage_id, "dataset_label": dataset_label},
        outputs={"benchmark_id": benchmark_id}, parents=(model_lineage_id,), created_at=created_at)


def make_evaluation_lineage(evaluation_marker: str, benchmark_lineage_id: str, *,
                            created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="validation_evaluation", versions=clinical_version_bundle(),
        inputs={"benchmark_id": benchmark_lineage_id},
        outputs={"evaluation_marker": evaluation_marker}, parents=(benchmark_lineage_id,),
        created_at=created_at)


def make_evidence_lineage(evidence_id: str, evaluation_lineage_id: str, *,
                          created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="validation_evidence", versions=clinical_version_bundle(),
        inputs={"evaluation_id": evaluation_lineage_id}, outputs={"evidence_id": evidence_id},
        parents=(evaluation_lineage_id,), created_at=created_at)


def make_readiness_lineage(readiness_id: str, evidence_lineage_id: str, *, classification: str,
                           created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="validation_readiness", versions=clinical_version_bundle(),
        inputs={"evidence_id": evidence_lineage_id},
        outputs={"readiness_id": readiness_id, "classification": classification},
        parents=(evidence_lineage_id,), created_at=created_at)
