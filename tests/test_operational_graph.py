"""Tests for the Operational Knowledge Graph (V3-P4).

Covers the node system, edge system, relationship engine, ontology, registry,
query layer, projections, lineage, validation, determinism, and the governance
gate — over a graph derived from real entities/events/workflows.
"""

from __future__ import annotations

import pytest

from backend.operational_graph import (
    OperationalGraphService, GraphInput, NodeSpec, EdgeSpec, NodeType, EdgeType,
    GraphGovernanceGate, ontology,
)
from backend.operational_graph.ontology import edge_allowed

from _v3b_helpers import build_v3b


@pytest.fixture(scope="module")
def fx():
    return build_v3b(2)


@pytest.fixture(scope="module")
def graph(fx):
    return fx.graph


# --- node + edge systems ------------------------------------------------------
def test_nodes_represent_real_sources(graph):
    for nid in graph.registry.list_nodes():
        node = graph.registry.node(nid)
        assert node.source_id                       # no graph-only truth
        assert ontology.is_node_type(node.node_type)


def test_edges_are_ontology_valid(graph):
    for eid in graph.registry.list_edges():
        e = graph.registry.edge(eid)
        assert edge_allowed(e.edge_type, e.source_type, e.target_type)
        assert e.derived_from                        # justified by a real artifact


def test_node_identity_is_source_addressed():
    a = build_v3b(2)
    b = build_v3b(2)
    assert a.graph.registry.list_nodes() == b.graph.registry.list_nodes()


# --- ontology -----------------------------------------------------------------
def test_ontology_constrains_pairings():
    assert edge_allowed(EdgeType.OWNS, NodeType.PATIENT, NodeType.CASE)
    assert not edge_allowed(EdgeType.OWNS, NodeType.CASE, NodeType.PATIENT)
    assert not edge_allowed("not_an_edge", NodeType.CASE, NodeType.REVIEW)


def test_relationship_engine_rejects_invalid_edges(fx):
    g = OperationalGraphService(lineage_tracker=fx.base.cs.lineage)
    gi = GraphInput()
    cid = next(iter(fx.base.cases))
    c = fx.base.cases[cid]
    gi.add_node(NodeSpec(NodeType.PATIENT, c.patient_id, c.lineage_id))
    gi.add_node(NodeSpec(NodeType.CASE, cid, c.lineage_id))
    # invalid: case OWNS patient (reverse of the only allowed owns pairing)
    gi.add_edge(EdgeSpec(EdgeType.OWNS, cid, c.patient_id, derived_from=(cid,)))
    result = g.build_graph(gi)
    assert result["n_nodes"] == 2
    assert result["n_edges"] == 0                    # the invalid edge was dropped


# --- registry -----------------------------------------------------------------
def test_no_artifact_outside_registry(graph):
    for nid in graph.registry.list_nodes():
        assert graph.registry.exists(nid)
    for eid in graph.registry.list_edges():
        assert graph.registry.exists(eid)


# --- query layer --------------------------------------------------------------
def test_node_and_relationship_lookup(graph, fx):
    case_id = next(iter(fx.base.cases))
    node = graph.registry.node_by_source(case_id)
    assert node is not None
    looked = graph.queries.node_lookup(node.node_id)
    assert looked["source_id"] == case_id
    rels = graph.queries.relationship_lookup(node.node_id)
    assert "out_edges" in rels and "in_edges" in rels


def test_neighborhood_and_traversals(graph, fx):
    case_id = next(iter(fx.base.cases))
    node = graph.registry.node_by_source(case_id)
    nb = graph.queries.neighborhood(node.node_id, depth=2)
    assert node.node_id in nb["nodes"]
    assert len(nb["nodes"]) >= 2
    # workflow traversal follows contains/produces/precedes
    wf_reach = graph.queries.workflow_traversal(node.node_id)
    assert isinstance(wf_reach, list)


def test_query_by_type(graph):
    q = graph.queries.query(node_type=NodeType.CASE)
    assert all(graph.registry.node(nid).node_type == NodeType.CASE for nid in q["nodes"])


# --- projections --------------------------------------------------------------
def test_projection_is_induced_subgraph(graph):
    proj = graph.projections.by_node_types("case", [NodeType.CASE, NodeType.REVIEW, NodeType.FINDING])
    proj = graph.build_projection(proj)
    assert proj.n_nodes >= 1
    # every projected edge connects two projected nodes
    node_set = set(proj.node_ids)
    for eid in proj.edge_ids:
        e = graph.registry.edge(eid)
        assert e.source_node in node_set and e.target_node in node_set
    assert graph.validate(proj).ok


def test_operational_projection(graph):
    proj = graph.build_projection(graph.projections.operational())
    assert proj.n_nodes == len(graph.registry.list_nodes())
    assert proj.n_edges == len(graph.registry.list_edges())


# --- lineage / validation -----------------------------------------------------
def test_graph_node_lineage_traces_to_patient(graph, fx):
    case_id = next(iter(fx.base.cases))
    node = graph.registry.node_by_source(case_id)
    kinds = {r.kind for r in fx.base.cs.lineage.chain(node.lineage_id)}
    assert {"graph_node", "case", "patient"} <= kinds
    assert fx.base.cs.lineage.verify_chain(node.lineage_id)


def test_full_graph_validation_passes(graph):
    for nid in graph.registry.list_nodes():
        rep = graph.validate(graph.registry.node(nid)).to_dict()
        assert rep["ok"], rep
        names = {c["name"] for c in rep["checks"]}
        assert {"node_integrity", "ontology_integrity", "registry_integrity",
                "audit_integrity", "lineage_integrity", "version_integrity"} <= names
    for eid in graph.registry.list_edges():
        assert graph.validate(graph.registry.edge(eid)).ok


def test_governance_gate_rejects_graph_only_truth():
    from backend.operational_graph.nodes.domain import GraphNode
    bad = GraphNode(node_id="gnode+" + "0" * 16, node_type="case", source_id="")
    gate = GraphGovernanceGate()
    report = gate.evaluate(artifact=bad, parents=(), requires_lineage=False)
    assert not report.ok
    assert "risk_validation" in {c.name for c in report.failures()}


def test_graph_audit_verifies(graph):
    assert graph.audit.verify()
    assert len(graph.audit) > 0
