"""Governance-intelligence lineage helpers built on ml.lineage.

Every governance-intelligence record gets a content-addressed lineage node whose
parents are the lineage nodes of the governed artifacts it observed (goals,
policies, plans, tasks, agents, executions). Because those nodes trace through their
own chains to the patient, ``verify_chain`` from a governance-intelligence node spans
the whole deliverable chain Patient -> ... -> Goal -> ... -> Execution ->
Governance Intelligence.

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    GOVERNANCE_INTELLIGENCE_VERSION, GOVERNANCE_DOMAIN_VERSION, GOVERNANCE_IDENTITY_VERSION,
    GOVERNANCE_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def governance_version_bundle(**extra: object) -> dict:
    bundle = {
        "governance_intelligence_version": GOVERNANCE_INTELLIGENCE_VERSION,
        "governance_domain_version": GOVERNANCE_DOMAIN_VERSION,
        "governance_identity_version": GOVERNANCE_IDENTITY_VERSION,
        "governance_lineage_version": GOVERNANCE_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_governance_lineage(intelligence_id: str, *, parents: Sequence[str] = (),
                            scope: str = "", reason: str = "created",
                            created_at: str = DETERMINISTIC_EPOCH,
                            extra: dict | None = None) -> LineageRecord:
    """A governance-intelligence lineage node parented by the observed artifacts' nodes."""
    outputs = {"intelligence_id": intelligence_id, "reason": reason}
    if extra:
        outputs.update(extra)
    return make_lineage_record(
        kind="governance_intelligence", versions=governance_version_bundle(),
        inputs={"intelligence_id": intelligence_id, "scope": scope,
                "n_parents": len(tuple(parents))},
        outputs=outputs, parents=tuple(p for p in parents if p), created_at=created_at)
