"""Shared builders for the V3-P3 / V3-P4 test suites.

Extends the V3-P1/P2 fixture with derived workflows (V3-P3) and a derived
operational graph (V3-P4), all over one shared lineage tracker. Not collected by
pytest (no ``test_`` prefix).
"""

from __future__ import annotations

from dataclasses import dataclass

from _v3_helpers import build_v3, V3Fixture

from backend.workflow_intelligence import WorkflowIntelligenceService, EntityRef
from backend.operational_graph import (
    OperationalGraphService, GraphInput, NodeSpec, EdgeSpec, NodeType, EdgeType,
)


@dataclass
class V3bFixture:
    base: V3Fixture
    workflows: WorkflowIntelligenceService
    workflow_records: dict          # workflow_id -> WorkflowRecord
    graph: OperationalGraphService


def _entity_refs(base: V3Fixture, case_id: str) -> list:
    review_ids = [r.review_id for r in base.reviews.values() if r.case_id == case_id]
    finding_ids = [f.finding_id for f in base.findings.values() if f.case_id == case_id]
    refs = [EntityRef(case_id, "case", None, completed=True)]
    refs += [EntityRef(rid, "review", case_id, completed=True) for rid in review_ids]
    parent_review = review_ids[0] if review_ids else case_id
    refs += [EntityRef(fid, "finding", parent_review, completed=True) for fid in finding_ids]
    return refs


def build_v3b(n_cases: int = 2) -> V3bFixture:
    base = build_v3(n_cases)

    # --- V3-P3 workflows (one per case) ----------------------------------
    wi = WorkflowIntelligenceService(base.events).load_events(base.all_events)
    workflow_records: dict = {}
    for case_id in base.cases:
        wf = wi.build_workflow(workflow_type="case_workflow", subject_kind="case",
                               subject_id=case_id, source_entity_ids=[case_id],
                               dependency_refs=_entity_refs(base, case_id))
        workflow_records[wf.workflow_id] = wf
    # an operational workflow over all events
    op_wf = wi.build_operational_workflow()
    workflow_records[op_wf.workflow_id] = op_wf

    # --- V3-P4 operational graph (derived from entities/events/workflows) -
    g = OperationalGraphService(lineage_tracker=base.cs.lineage)
    gi = GraphInput()
    seen_patients = set()
    for cid, c in base.cases.items():
        if c.patient_id not in seen_patients:
            gi.add_node(NodeSpec(NodeType.PATIENT, c.patient_id, c.lineage_id, label="patient"))
            seen_patients.add(c.patient_id)
        gi.add_node(NodeSpec(NodeType.CASE, cid, c.lineage_id, label="case"))
        gi.add_edge(EdgeSpec(EdgeType.OWNS, c.patient_id, cid, derived_from=(cid,)))
    for rid, r in base.reviews.items():
        gi.add_node(NodeSpec(NodeType.REVIEW, rid, r.lineage_id, label="review"))
        gi.add_edge(EdgeSpec(EdgeType.CONTAINS, r.case_id, rid, derived_from=(rid,)))
    for fid, f in base.findings.items():
        gi.add_node(NodeSpec(NodeType.FINDING, fid, f.lineage_id, label="finding"))
        gi.add_edge(EdgeSpec(EdgeType.PRODUCES, f.review_id, fid, derived_from=(fid,)))
    # workflow nodes derived from their case
    for wid, wf in workflow_records.items():
        if wf.subject_kind == "case":
            gi.add_node(NodeSpec(NodeType.WORKFLOW, wid, wf.lineage_id, label="workflow"))
            gi.add_edge(EdgeSpec(EdgeType.DERIVED_FROM, wid, wf.subject_id, derived_from=(wid,)))
    g.build_graph(gi)

    return V3bFixture(base=base, workflows=wi, workflow_records=workflow_records, graph=g)
