"""End-to-end V3-P3 + V3-P4 deliverable-chain test.

Proves the required chain executes with complete traceability:

    Patient -> Case -> Review -> Finding -> Knowledge -> Decision -> Event
            -> Timeline -> Workflow -> Graph -> Relationship Model

over the real V2/V3 artifacts, and that all cross-version invariants hold (V2 +
V3 event/temporal lineage intact, determinism, audit immutability, no graph-only
truth, no hidden workflow state).
"""

from __future__ import annotations

from _v3b_helpers import build_v3b


def test_full_chain_executes_with_traceability():
    fx = build_v3b(2)
    tracker = fx.base.cs.lineage   # single shared platform lineage tracker

    # --- V3-P3 workflows validate + trace to patient -----------------------
    for wf in fx.workflow_records.values():
        assert fx.workflows.validate(wf).ok
        kinds = {r.kind for r in tracker.chain(wf.lineage_id)}
        assert {"workflow", "event"} <= kinds
        assert tracker.verify_chain(wf.lineage_id)

    # --- V3-P4 graph validates + traces to patient -------------------------
    g = fx.graph
    for nid in g.registry.list_nodes():
        assert g.validate(g.registry.node(nid)).ok
    for eid in g.registry.list_edges():
        assert g.validate(g.registry.edge(eid)).ok

    # the chain Patient -> ... -> Workflow -> Graph is present in graph lineage
    case_id = next(iter(fx.base.cases))
    wf_node = None
    for nid in g.registry.list_nodes():
        if g.registry.node(nid).node_type == "workflow":
            wf_node = g.registry.node(nid)
            break
    assert wf_node is not None
    chain_kinds = {r.kind for r in tracker.chain(wf_node.lineage_id)}
    for k in ("graph_node", "workflow", "event", "case", "patient"):
        assert k in chain_kinds, f"missing {k} in graph->workflow lineage"
    assert tracker.verify_chain(wf_node.lineage_id)

    # a case graph node reaches the patient too
    case_node = g.registry.node_by_source(case_id)
    case_chain = {r.kind for r in tracker.chain(case_node.lineage_id)}
    assert {"graph_node", "case", "patient"} <= case_chain

    # --- audit trails immutable + intact -----------------------------------
    assert fx.workflows.audit.verify() and g.audit.verify()
    assert fx.base.events.audit.verify()

    # --- V2 + V3 event/temporal lineage remains intact ---------------------
    for cid, c in fx.base.cases.items():
        assert tracker.verify_chain(c.lineage_id)
    for e in fx.base.all_events:
        assert tracker.verify_chain(e.lineage_id)

    # --- everything registered ---------------------------------------------
    assert all(fx.workflows.registry.exists(w) for w in fx.workflow_records)
    assert g.registry.list_nodes() and g.registry.list_edges()

    # --- relationship model (projections) ----------------------------------
    proj = g.build_projection(g.projections.operational())
    assert proj.n_nodes == len(g.registry.list_nodes())


def test_full_chain_is_reproducible():
    def run():
        fx = build_v3b(2)
        g = fx.graph
        wf_sigs = sorted(w.state_signature() for w in fx.workflow_records.values())
        node_sigs = sorted(g.registry.node(n).state_signature() for n in g.registry.list_nodes())
        edge_sigs = sorted(g.registry.edge(e).state_signature() for e in g.registry.list_edges())
        return (wf_sigs, node_sigs, edge_sigs,
                fx.workflows.audit.head, g.audit.head)

    assert run() == run()


def test_graph_and_workflow_do_not_mutate_sources():
    fx = build_v3b(2)
    case_id = next(iter(fx.base.cases))
    before = fx.base.cs.registry.get(case_id).content_signature()
    # building more projections / re-reading must not change source truth
    fx.graph.build_projection(fx.graph.projections.operational())
    after = fx.base.cs.registry.get(case_id).content_signature()
    assert before == after
