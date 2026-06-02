"""Multi-case intelligence lineage helpers built on ml.lineage.

Every intelligence artifact gets a content-addressed lineage node whose *parents*
are the lineage nodes of the source aggregates it was derived from (case/review/
finding/interpretation/concept nodes in the shared tracker). A single
``verify_chain`` from an intelligence node therefore spans back to the patient
roots — the deliverable's complete traceability.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    MULTI_CASE_INTELLIGENCE_VERSION, INTEL_DOMAIN_VERSION, INTEL_IDENTITY_VERSION,
    INTEL_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def intel_version_bundle(**extra: object) -> dict:
    bundle = {
        "multi_case_intelligence_version": MULTI_CASE_INTELLIGENCE_VERSION,
        "intel_domain_version": INTEL_DOMAIN_VERSION,
        "intel_identity_version": INTEL_IDENTITY_VERSION,
        "intel_lineage_version": INTEL_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_intel_lineage(kind: str, artifact_id: str, *, parents: Sequence[str] = (),
                       scope: str = "", created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A generic intelligence lineage node parented by its source nodes."""
    return make_lineage_record(
        kind=kind, versions=intel_version_bundle(),
        inputs={"artifact_id": artifact_id, "scope": scope, "n_parents": len(tuple(parents))},
        outputs={"artifact_id": artifact_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
