"""Graph validation checks + the governance gate (V3-P4).

``GraphValidator`` verifies node/edge/relationship/ontology integrity plus
registry/audit/lineage/version integrity. ``GraphGovernanceGate`` enforces the four
constitutional per-workflow validations — Architecture, Quality, Context, Risk —
before a graph artifact is admitted. The "risk" dimension enforces *derived* (every
node/edge references a real source artifact; no graph-only truth).
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_node_id, validate_edge_id, validate_projection_id
from ..ontology import is_node_type, is_edge_type, edge_allowed
from ..nodes.domain import GraphNode, GraphEdge, GraphProjection, GraphVersion


def _id_ok(artifact) -> bool:
    if isinstance(artifact, GraphNode):
        return validate_node_id(artifact.node_id)[0]
    if isinstance(artifact, GraphEdge):
        return validate_edge_id(artifact.edge_id)[0]
    if isinstance(artifact, GraphProjection):
        return validate_projection_id(artifact.projection_id)[0]
    return False


def _artifact_id(artifact) -> str:
    if isinstance(artifact, GraphNode):
        return artifact.node_id
    if isinstance(artifact, GraphEdge):
        return artifact.edge_id
    if isinstance(artifact, GraphProjection):
        return artifact.projection_id
    raise ValueError(f"unrecognised graph artifact {type(artifact)!r}")


def _derived_ok(artifact) -> bool:
    """Every node/edge must be derived from a real source (no graph-only truth)."""
    if isinstance(artifact, GraphNode):
        return bool(artifact.source_id)
    if isinstance(artifact, GraphEdge):
        return bool(artifact.source_node) and bool(artifact.target_node)
    if isinstance(artifact, GraphProjection):
        return True  # a projection is a view over existing artifacts
    return False


def _ontology_ok(artifact) -> bool:
    if isinstance(artifact, GraphNode):
        return is_node_type(artifact.node_type)
    if isinstance(artifact, GraphEdge):
        return (is_edge_type(artifact.edge_type)
                and edge_allowed(artifact.edge_type, artifact.source_type, artifact.target_type))
    return True


class GraphValidationError(RuntimeError):
    """Raised when a mandated graph-validation check fails."""


class GraphGovernanceGate:
    """The architecture/quality/context/risk gate every graph artifact must pass."""

    def evaluate(self, *, artifact: Any, parents: tuple = (),
                 requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        report.add("architecture_validation", _ontology_ok(artifact), "conforms to ontology")
        report.add("quality_validation", _id_ok(artifact), "well-formed identity")
        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")
        report.add("risk_validation", _derived_ok(artifact),
                   "derived from a real source" if _derived_ok(artifact)
                   else "not derived (graph-only truth forbidden)")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise GraphValidationError(f"graph governance gate rejected: {names}")


class GraphValidator:
    """Validates integrity of a registered graph artifact (the eight dimensions)."""

    def validate(self, *, artifact: Any, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        aid = _artifact_id(artifact)
        is_node = isinstance(artifact, GraphNode)
        is_edge = isinstance(artifact, GraphEdge)

        report.add("node_integrity", (not is_node) or (_id_ok(artifact) and _derived_ok(artifact)),
                   "node well-formed + derived" if is_node else "n/a")
        report.add("edge_integrity", (not is_edge) or (_id_ok(artifact) and _ontology_ok(artifact)),
                   "edge well-formed + ontology-valid" if is_edge else "n/a")
        # relationship integrity: an edge's endpoints exist in the registry
        rel_ok = True
        if is_edge:
            rel_ok = registry.has_node(artifact.source_node) and registry.has_node(artifact.target_node)
        report.add("relationship_integrity", rel_ok,
                   "edge endpoints registered" if is_edge else "n/a")
        report.add("ontology_integrity", _ontology_ok(artifact), "conforms to ontology")

        try:
            rec = registry.get_record(aid)
            ok = rec.version == artifact.version and rec.lineage_id == (artifact.lineage_id or "")
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} artifact version={artifact.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (artifact.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        try:
            chain_ok = bool(artifact.lineage_id) and lineage_tracker.verify_chain(artifact.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        try:
            expected = GraphVersion.compute(artifact.state_signature(), None)
            report.add("version_integrity", artifact.version == expected,
                       f"recorded={artifact.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report
