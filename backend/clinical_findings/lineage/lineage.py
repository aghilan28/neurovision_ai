"""Clinical-finding lineage helpers built on ml.lineage."""

from __future__ import annotations

from typing import Optional

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    CLINICAL_FINDINGS_VERSION, FINDING_DOMAIN_VERSION, FINDING_IDENTITY_VERSION,
    FINDING_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def finding_version_bundle(**extra: object) -> dict:
    bundle = {
        "clinical_findings_version": CLINICAL_FINDINGS_VERSION,
        "finding_domain_version": FINDING_DOMAIN_VERSION,
        "finding_identity_version": FINDING_IDENTITY_VERSION,
        "finding_lineage_version": FINDING_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_evidence_lineage(evidence_id: str, finding_id: str, *, source_lineage_id: Optional[str],
                          evidence_type: str, created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """An evidence node; parent = the source artifact's lineage node (e.g. inference)."""
    parents = (source_lineage_id,) if source_lineage_id else ()
    return make_lineage_record(
        kind="evidence", versions=finding_version_bundle(),
        inputs={"finding_id": finding_id, "evidence_id": evidence_id, "evidence_type": evidence_type},
        outputs={"evidence_id": evidence_id}, parents=parents, created_at=created_at)


def make_finding_lineage(finding_id: str, *, review_lineage_id: Optional[str],
                         evidence_lineage_ids: tuple = (), created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A finding node; parents = review node + the evidence nodes it rests on."""
    parents = []
    if review_lineage_id:
        parents.append(review_lineage_id)
    parents.extend(evidence_lineage_ids)
    return make_lineage_record(
        kind="finding", versions=finding_version_bundle(),
        inputs={"finding_id": finding_id}, outputs={"finding_id": finding_id},
        parents=tuple(parents), created_at=created_at)


def make_interpretation_lineage(interpretation_id: str, finding_id: str, *, finding_lineage_id: str,
                                created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="interpretation", versions=finding_version_bundle(),
        inputs={"finding_id": finding_id, "interpretation_id": interpretation_id},
        outputs={"interpretation_id": interpretation_id}, parents=(finding_lineage_id,),
        created_at=created_at)
