"""Build the Operational Intelligence Workstation snapshot (V3-P7).

This is the **only** seam between the backend V3 domain subsystems and the frontend
operational workstation. It composes the real V3 services — Operational Events
(V3-P1), Temporal Intelligence (V3-P2), Workflow Intelligence (V3-P3), the
Operational Graph (V3-P4), Operational Analytics (V3-P5) and Operational
Recommendations (V3-P6) — over **one shared lineage tracker**, driving a small
deterministic multi-case workflow through the real V2 services first, and
serializes every *registered artifact* (registries, reports, immutable audit logs,
the lineage graph, validation results) into a single JSON snapshot.

The frontend (``frontend/operational_workstation``) reads that snapshot with stdlib
``json`` only and imports **no** domain module (NR-8). Scripts may import any layer;
this is the sanctioned composition point (like ``build_workstation_snapshot``).

    python -m scripts.build_operational_workstation_snapshot --out op_snapshot.json

The snapshot is deterministic (DETERMINISTIC_EPOCH everywhere; no wall-clock), so
the same inputs always produce a byte-identical file.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Optional

from backend.clinical_cases import CaseService, CaseStatus
from backend.clinical_review import ReviewService
from backend.clinical_findings import FindingService, FindingRecord, evidence_spec
from backend.clinical_knowledge import KnowledgeService
from backend.operational_events import OperationalEventService
from backend.operational_events.generation import (
    CaseEventAdapter, ReviewEventAdapter, FindingEventAdapter, KnowledgeEventAdapter,
)
from backend.temporal_intelligence import TemporalIntelligenceService
from backend.workflow_intelligence import WorkflowIntelligenceService, EntityRef
from backend.operational_graph import (
    OperationalGraphService, GraphInput, NodeSpec, EdgeSpec, NodeType, EdgeType,
)
from backend.operational_analytics import OperationalAnalyticsService
from backend.operational_recommendations import OperationalRecommendationService

SNAPSHOT_VERSION = "operational-workstation-snapshot@1.0.0"
EPOCH = "1970-01-01T00:00:00Z"



def _audit(log) -> dict:
    """Serialize an ImmutableAuditLog (+ its verified flag)."""
    d = log.to_dict()
    d["verified"] = log.verify()
    return d


def _full_case(cs, rs, fs, patient, enc, category, conf):
    """Drive one case through the full V2 lifecycle (case -> review -> finding)."""
    case = cs.create_case(patient_key=patient, case_key=enc, owner="ops")
    for st in (CaseStatus.INGESTED, CaseStatus.PROCESSING, CaseStatus.READY_FOR_REVIEW,
               CaseStatus.UNDER_REVIEW, CaseStatus.REVIEWED):
        cs.transition(case, st, "x")
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                              study_id=None, inference_lineage_id=None, artifact_refs=())
    rs.assign(review, assignee="dr.reviewer")
    review, sess = rs.start_session(review)
    review, sess = rs.end_session(review, sess, outcome="confirmed", notes="ok")
    rs.submit_for_confirmation(review)
    rs.complete(review)
    finding = fs.create_finding(
        review_id=review.review_id, case_id=case.case_id, study_id=None,
        record=FindingRecord(observation=category, category=category),
        evidence_specs=[
            evidence_spec("inference", f"inf-{enc}", "output-contract@1.0.0", confidence=conf),
            evidence_spec("coverage", f"cov-{enc}", "coverage@1.0.0",
                          confidence=min(0.99, conf + 0.03))],
        review_lineage_id=review.lineage_id)
    finding, _ = fs.add_interpretation(finding, text=f"{category} pattern", confidence_level="high")
    finding = fs.to_draft(finding)
    finding = fs.submit_for_review(finding)
    finding = fs.confirm(finding)
    return case, review, finding


def _generate_events(evs, cs, rs, fs, ks, cases, reviews, findings) -> list:
    """Observe the V2 audit logs with the V3-P1 adapters to produce events."""
    all_events, ordinal = [], 0
    for c in cases.values():
        all_events += CaseEventAdapter(evs).observe_log(
            source_entity_id=c.case_id, source_version=cs.registry.get(c.case_id).version,
            audit_log=cs.audit_log_for(c.case_id), source_lineage_id=c.lineage_id,
            ingestion_ordinal=ordinal, created_at=EPOCH)
        ordinal += 1
    for r in reviews.values():
        all_events += ReviewEventAdapter(evs).observe_log(
            source_entity_id=r.review_id, source_version=rs.registry.get(r.review_id).version,
            audit_log=rs.audit_log_for(r.review_id), source_lineage_id=r.lineage_id,
            ingestion_ordinal=ordinal, created_at=EPOCH)
        ordinal += 1
    for f in findings.values():
        all_events += FindingEventAdapter(evs).observe_log(
            source_entity_id=f.finding_id, source_version=fs.registry.get(f.finding_id).version,
            audit_log=fs.audit_log_for(f.finding_id), source_lineage_id=f.lineage_id,
            ingestion_ordinal=ordinal, created_at=EPOCH)
        ordinal += 1
    all_events += KnowledgeEventAdapter(evs).observe_log(
        source_entity_id="knowledge",
        source_version=ks.registry.to_dict().get("knowledge_registry_version", "v1"),
        audit_log=ks.audit, source_lineage_id=ks.head_lineage_id,
        ingestion_ordinal=ordinal, created_at=EPOCH)
    return all_events



def _entity_refs(reviews, findings, case_id: str) -> list:
    """Dependency refs for a case workflow (case -> its reviews -> its findings)."""
    review_ids = [r.review_id for r in reviews.values() if r.case_id == case_id]
    finding_ids = [f.finding_id for f in findings.values() if f.case_id == case_id]
    refs = [EntityRef(case_id, "case", None, completed=True)]
    refs += [EntityRef(rid, "review", case_id, completed=True) for rid in review_ids]
    parent_review = review_ids[0] if review_ids else case_id
    refs += [EntityRef(fid, "finding", parent_review, completed=True) for fid in finding_ids]
    return refs


def _build_workflows(events_service, all_events, cases, reviews, findings) -> tuple:
    """Derive one workflow per case + an operational workflow (V3-P3)."""
    wi = WorkflowIntelligenceService(events_service).load_events(all_events)
    records: dict = {}
    for case_id in cases:
        wf = wi.build_workflow(workflow_type="case_workflow", subject_kind="case",
                               subject_id=case_id, source_entity_ids=[case_id],
                               dependency_refs=_entity_refs(reviews, findings, case_id))
        records[wf.workflow_id] = wf
    op_wf = wi.build_operational_workflow()
    records[op_wf.workflow_id] = op_wf
    return wi, records


def _build_graph(tracker, cases, reviews, findings, workflow_records):
    """Derive the operational graph from V2 entities + V3 workflows (V3-P4)."""
    g = OperationalGraphService(lineage_tracker=tracker)
    gi = GraphInput()
    seen_patients = set()
    for cid, c in cases.items():
        if c.patient_id not in seen_patients:
            gi.add_node(NodeSpec(NodeType.PATIENT, c.patient_id, c.lineage_id, label="patient"))
            seen_patients.add(c.patient_id)
        gi.add_node(NodeSpec(NodeType.CASE, cid, c.lineage_id, label="case"))
        gi.add_edge(EdgeSpec(EdgeType.OWNS, c.patient_id, cid, derived_from=(cid,)))
    for rid, r in reviews.items():
        gi.add_node(NodeSpec(NodeType.REVIEW, rid, r.lineage_id, label="review"))
        gi.add_edge(EdgeSpec(EdgeType.CONTAINS, r.case_id, rid, derived_from=(rid,)))
    for fid, f in findings.items():
        gi.add_node(NodeSpec(NodeType.FINDING, fid, f.lineage_id, label="finding"))
        gi.add_edge(EdgeSpec(EdgeType.PRODUCES, f.review_id, fid, derived_from=(fid,)))
    for wid, wf in workflow_records.items():
        if wf.subject_kind == "case":
            gi.add_node(NodeSpec(NodeType.WORKFLOW, wid, wf.lineage_id, label="workflow"))
            gi.add_edge(EdgeSpec(EdgeType.DERIVED_FROM, wid, wf.subject_id, derived_from=(wid,)))
    g.build_graph(gi)
    # a derived operational projection (whole-graph view)
    projection = g.build_projection(g.projections.operational())
    return g, projection



def build_snapshot(*, n_cases: int = 3) -> dict:
    """Compose the real V3 services over one lineage tracker and serialize them.

    Returns a plain JSON-able dict — the Operational Workstation snapshot.
    """
    # --- V2 base workflow over ONE shared lineage tracker --------------------
    cs = CaseService()
    tracker = cs.lineage
    ks = KnowledgeService(lineage_tracker=tracker).seed_default_knowledge()
    rs = ReviewService(lineage_tracker=tracker)
    fs = FindingService(lineage_tracker=tracker)

    plan = [("PT-001", "ENC-1", "LPD", 0.91), ("PT-002", "ENC-2", "GPD", 0.62),
            ("PT-003", "ENC-3", "SZ", 0.88), ("PT-004", "ENC-4", "GRDA", 0.34),
            ("PT-005", "ENC-5", "LRDA", 0.77)][:n_cases]
    cases, reviews, findings = {}, {}, {}
    for patient, enc, cat, conf in plan:
        c, r, f = _full_case(cs, rs, fs, patient, enc, cat, conf)
        cases[c.case_id] = c
        reviews[r.review_id] = r
        findings[f.finding_id] = f

    # --- V3-P1 events --------------------------------------------------------
    evs = OperationalEventService(lineage_tracker=tracker)
    all_events = _generate_events(evs, cs, rs, fs, ks, cases, reviews, findings)

    # --- V3-P2 temporal ------------------------------------------------------
    ti = TemporalIntelligenceService(evs, lineage_tracker=tracker).load_events(all_events)
    temporal_analytics = ti.build_analytics(scope="operational")
    op_timeline = ti.build_operational_timeline()
    # one representative subject timeline/history/evolution (first case)
    first_case = next(iter(cases))
    subj_timeline = ti.build_timeline(subject_kind="case", subject_id=first_case,
                                      source_entity_ids=[first_case])
    subj_history = ti.build_history(subject_kind="case", subject_id=first_case,
                                    source_entity_ids=[first_case])
    subj_evolution = ti.build_evolution(subject_kind="case", subject_id=first_case,
                                        source_entity_ids=[first_case])

    # --- V3-P3 workflows -----------------------------------------------------
    wi, workflow_records = _build_workflows(evs, all_events, cases, reviews, findings)

    # --- V3-P4 graph ---------------------------------------------------------
    g, projection = _build_graph(tracker, cases, reviews, findings, workflow_records)

    # --- V3-P5 analytics -----------------------------------------------------
    oa = OperationalAnalyticsService(lineage_tracker=tracker)
    oa.load_sources(events=all_events, workflows=list(workflow_records.values()),
                    graph_registry=g.registry, temporal_analytics=temporal_analytics)
    analytics_records = oa.build_all()

    # --- V3-P6 recommendations ----------------------------------------------
    orr = OperationalRecommendationService(lineage_tracker=tracker)
    orr.load_intelligence(analytics=list(analytics_records.values()),
                          workflows=list(workflow_records.values()), graph_registry=g.registry)
    produced = orr.generate()

    return _serialize(
        tracker=tracker, cases=cases, reviews=reviews, findings=findings,
        events_service=evs, all_events=all_events, ti=ti,
        temporal_analytics=temporal_analytics, op_timeline=op_timeline,
        subj_timeline=subj_timeline, subj_history=subj_history, subj_evolution=subj_evolution,
        wi=wi, workflow_records=workflow_records, graph=g, projection=projection,
        analytics_service=oa, analytics_records=analytics_records,
        recommendation_service=orr, produced=produced)



def _events_block(evs, all_events) -> dict:
    """Serialize the event registry, taxonomy, reports, audit, and per-event records."""
    events = [{"event_id": e.event_id, "event_type": e.event_type, "category": e.category,
               "source_entity_id": e.source_entity_id, "version": e.version,
               "lineage_id": e.lineage_id, "status": e.status,
               "lineage_verified": evs.lineage.verify_chain(e.lineage_id)}
              for e in all_events]
    reports = evs.reports()
    # one representative event validation (first event)
    validation = evs.validate(all_events[0]).to_dict() if all_events else {"ok": True, "checks": []}
    return {
        "registry": evs.registry.to_dict(),
        "reports": reports,
        "taxonomy": reports.get("event_taxonomy_report", {}),
        "audit": _audit(evs.audit),
        "events": events,
        "n_events": len(events),
        "representative_validation": validation,
    }


def _timelines_block(ti, *, op_timeline, subj_timeline, subj_history, subj_evolution,
                     temporal_analytics) -> dict:
    """Serialize timelines, histories, evolution records, and temporal analytics."""
    return {
        "registry": ti.registry.to_dict(),
        "audit": _audit(ti.audit),
        "operational_timeline": {
            "artifact": op_timeline.to_dict(),
            "validation": ti.validate(op_timeline, "timeline").to_dict(),
            "lineage_verified": ti.lineage.verify_chain(op_timeline.lineage_id)},
        "timeline": {"artifact": subj_timeline.to_dict(),
                     "validation": ti.validate(subj_timeline, "timeline").to_dict()},
        "history": {"artifact": subj_history.to_dict(),
                    "validation": ti.validate(subj_history, "history").to_dict()},
        "evolution": {"artifact": subj_evolution.to_dict(),
                      "validation": ti.validate(subj_evolution, "evolution").to_dict()},
        "analytics": {"artifact": temporal_analytics.to_dict(),
                      "validation": ti.validate(temporal_analytics, "analytics").to_dict(),
                      "lineage_verified": ti.lineage.verify_chain(temporal_analytics.lineage_id)},
        "reports": ti.reports(timeline=subj_timeline, history=subj_history,
                              evolution=subj_evolution, analytics=temporal_analytics),
    }



def _workflows_block(wi, workflow_records) -> dict:
    """Serialize the workflow registry, per-workflow records, reports, audit, lineage."""
    workflows = []
    for wid, wf in sorted(workflow_records.items()):
        workflows.append({
            "workflow_id": wid, "workflow_type": wf.workflow_type,
            "subject_kind": wf.subject_kind, "subject_id": wf.subject_id, "state": wf.state,
            "version": wf.version, "lineage_id": wf.lineage_id,
            "lineage_verified": wi.lineage.verify_chain(wf.lineage_id),
            "metrics": [m.to_dict() for m in wf.metrics],
            "bottlenecks": list(wf.metadata.bottlenecks),
            "reports": wi.reports(wf),
            "validation": wi.validate(wf).to_dict(),
        })
    return {
        "registry": wi.registry.to_dict(),
        "audit": _audit(wi.audit),
        "workflows": workflows,
        "n_workflows": len(workflows),
    }


def _graph_block(g, projection) -> dict:
    """Serialize the graph registry (nodes/edges/relationships/projections) + reports."""
    return {
        "registry": g.registry.to_dict(),
        "audit": _audit(g.audit),
        "reports": g.reports(),
        "projection": {
            "artifact": projection.to_dict(),
            "validation": g.validate(projection).to_dict(),
            "lineage_verified": g.lineage.verify_chain(projection.lineage_id)},
        "n_nodes": len(g.registry.list_nodes()),
        "n_edges": len(g.registry.list_edges()),
    }



def _analytics_block(oa, analytics_records) -> dict:
    """Serialize analytics records (per dimension), reports, audit, lineage."""
    records = list(analytics_records.values())
    blocks = {}
    for category, rec in analytics_records.items():
        blocks[category] = {
            "artifact": rec.to_dict(),
            "validation": oa.validate(rec).to_dict(),
            "lineage_verified": oa.lineage.verify_chain(rec.lineage_id),
        }
    reports = oa.reports(records)
    reports["quality_report"] = oa.quality_report(records)
    return {
        "registry": oa.registry.to_dict(),
        "audit": _audit(oa.audit),
        "blocks": blocks,
        "reports": reports,
        "n_analytics": len(records),
    }


def _recommendations_block(orr, produced) -> dict:
    """Serialize recommendation records (by kind), reports, audit, lineage, contexts."""
    all_records = []
    for recs in produced.values():
        all_records.extend(recs)
    records = []
    for rec in all_records:
        records.append({
            "recommendation_id": rec.recommendation_id, "kind": rec.kind,
            "subject_kind": rec.subject_kind, "subject_id": rec.subject_id,
            "statement": rec.statement, "priority": rec.priority.to_dict(),
            "evidence": [e.to_dict() for e in rec.evidence], "context_id": rec.context_id,
            "analytics_ids": list(rec.analytics_ids), "version": rec.version,
            "lineage_id": rec.lineage_id,
            "lineage_verified": orr.lineage.verify_chain(rec.lineage_id),
            "validation": orr.validate(rec).to_dict(),
        })
    return {
        "registry": orr.registry.to_dict(),
        "audit": _audit(orr.audit),
        "reports": orr.reports(all_records),
        "recommendations": records,
        "by_kind": {k: [r.recommendation_id for r in v] for k, v in produced.items()},
        "n_recommendations": len(records),
    }



def _representative_chain(tracker, produced) -> dict:
    """The end-to-end Patient -> ... -> Recommendation chain for the lineage explorer.

    A recommendation's lineage parents are analytics nodes, which trace through
    workflow/graph/event/temporal nodes to the case and patient — so the chain from
    any recommendation spans the whole deliverable chain.
    """
    rec = None
    for recs in produced.values():
        if recs:
            rec = recs[0]
            break
    if rec is None:
        return {"records": [], "verified": True, "anchor": None}
    chain = [r.to_dict() for r in tracker.chain(rec.lineage_id)]
    return {"records": chain, "verified": tracker.verify_chain(rec.lineage_id),
            "anchor": rec.recommendation_id}


def _serialize(*, tracker, cases, reviews, findings, events_service, all_events, ti,
               temporal_analytics, op_timeline, subj_timeline, subj_history, subj_evolution,
               wi, workflow_records, graph, projection, analytics_service, analytics_records,
               recommendation_service, produced) -> dict:
    """Assemble the full deterministic snapshot from registered artifacts only."""
    events_b = _events_block(events_service, all_events)
    timelines_b = _timelines_block(ti, op_timeline=op_timeline, subj_timeline=subj_timeline,
                                   subj_history=subj_history, subj_evolution=subj_evolution,
                                   temporal_analytics=temporal_analytics)
    workflows_b = _workflows_block(wi, workflow_records)
    graph_b = _graph_block(graph, projection)
    analytics_b = _analytics_block(analytics_service, analytics_records)
    recommendations_b = _recommendations_block(recommendation_service, produced)
    rep_chain = _representative_chain(tracker, produced)

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "source": ("registered artifacts only "
                   "(composed by scripts.build_operational_workstation_snapshot)"),
        "meta": {
            "n_cases": len(cases), "n_reviews": len(reviews), "n_findings": len(findings),
            "n_events": events_b["n_events"], "n_workflows": workflows_b["n_workflows"],
            "n_nodes": graph_b["n_nodes"], "n_edges": graph_b["n_edges"],
            "n_analytics": analytics_b["n_analytics"],
            "n_recommendations": recommendations_b["n_recommendations"],
            "patients": sorted({c.patient_id for c in cases.values()}),
        },
        "events": events_b,
        "timelines": timelines_b,
        "workflows": workflows_b,
        "graph": graph_b,
        "analytics": analytics_b,
        "recommendations": recommendations_b,
        "lineage": tracker.to_dict(),
        "representative_chain": rep_chain,
        "registries": {
            "event_registry": events_service.registry.to_dict(),
            "temporal_registry": ti.registry.to_dict(),
            "workflow_registry": wi.registry.to_dict(),
            "graph_registry": graph.registry.to_dict(),
            "analytics_registry": analytics_service.registry.to_dict(),
            "recommendation_registry": recommendation_service.registry.to_dict(),
        },
    }



def write_snapshot(out_path: str, *, n_cases: int = 3) -> str:
    snapshot = build_snapshot(n_cases=n_cases)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, sort_keys=True, separators=(",", ":"))
    return out_path


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(
        description="Build the Operational Intelligence Workstation snapshot (V3-P7).")
    p.add_argument("--out", default="operational_workstation_snapshot.json")
    p.add_argument("--cases", type=int, default=3)
    args = p.parse_args(argv)
    path = write_snapshot(args.out, n_cases=args.cases)
    snap = build_snapshot(n_cases=args.cases)
    m = snap["meta"]
    print(f"wrote {path}")
    print(f"snapshot_version : {snap['snapshot_version']}")
    print(f"events/workflows/nodes/analytics/recs : "
          f"{m['n_events']}/{m['n_workflows']}/{m['n_nodes']}/"
          f"{m['n_analytics']}/{m['n_recommendations']}")
    print(f"representative chain verified : {snap['representative_chain']['verified']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
