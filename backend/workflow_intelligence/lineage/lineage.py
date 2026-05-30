"""Workflow-intelligence lineage helpers built on ml.lineage.

Every workflow gets a content-addressed lineage node whose *parents* are the
lineage nodes of the **events** (and optionally the **timeline**) it was derived
from. Because each event/timeline node already traces back to its source entity and
the patient, a single ``verify_chain`` from a workflow spans Patient → ... → Event
→ (Timeline) → Workflow. Shares the platform's single ``ml.lineage.LineageTracker``.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    WORKFLOW_INTELLIGENCE_VERSION, WORKFLOW_DOMAIN_VERSION, WORKFLOW_IDENTITY_VERSION,
    WORKFLOW_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def workflow_version_bundle(**extra: object) -> dict:
    bundle = {
        "workflow_intelligence_version": WORKFLOW_INTELLIGENCE_VERSION,
        "workflow_domain_version": WORKFLOW_DOMAIN_VERSION,
        "workflow_identity_version": WORKFLOW_IDENTITY_VERSION,
        "workflow_lineage_version": WORKFLOW_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_workflow_lineage(workflow_id: str, *, parents: Sequence[str] = (),
                          workflow_type: str = "", created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A workflow lineage node parented by the event/timeline nodes it derives from."""
    return make_lineage_record(
        kind="workflow", versions=workflow_version_bundle(),
        inputs={"workflow_id": workflow_id, "workflow_type": workflow_type,
                "n_parents": len(tuple(parents))},
        outputs={"workflow_id": workflow_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
