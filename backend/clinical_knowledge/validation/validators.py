"""Knowledge validation checks (V2-P4)."""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity


class KnowledgeValidationError(RuntimeError):
    """Raised when a mandated knowledge-validation check fails."""


class KnowledgeValidator:
    def validate(self, *, terminology: Any, concepts: Any, taxonomy: Any, ontology: Any,
                 relationships: Any, registry: Any, audit_log: Any, lineage_tracker: Any,
                 head_lineage_id: str, version: str) -> ValidationReport:
        report = ValidationReport()

        # 1. terminology integrity
        try:
            ok = True
            detail = f"{len(terminology.list_terms())} term(s)"
            for tid in terminology.list_terms():
                t = terminology.get(tid)
                if not validate_identity(tid, "term")[0] or not t.definition or not t.source:
                    ok, detail = False, f"term {tid} malformed/incomplete"
                    break
            report.add("terminology_integrity", ok, detail)
        except Exception as exc:
            report.add("terminology_integrity", False, f"error: {exc}")

        # 2. taxonomy integrity
        try:
            ok, detail = taxonomy.check_consistency()
            report.add("taxonomy_integrity", ok, detail)
        except Exception as exc:
            report.add("taxonomy_integrity", False, f"error: {exc}")

        # 3. ontology integrity
        try:
            ok, violations = ontology.validate(concepts=concepts, terminology=terminology,
                                               taxonomy=taxonomy, relationships=relationships)
            report.add("ontology_integrity", ok, "ok" if ok else f"violations={violations[:3]}")
        except Exception as exc:
            report.add("ontology_integrity", False, f"error: {exc}")

        # 4. relationship integrity (endpoint kinds + known-entity endpoints registered)
        try:
            from ..relationships import PREDICATES
            ok = True
            detail = f"{len(relationships.list_relations())} relationship(s)"
            for rid in relationships.list_relations():
                r = relationships.get(rid)
                exp = PREDICATES.get(r.predicate)
                if exp is None or (r.subject_kind, r.object_kind) != exp:
                    ok, detail = False, f"relation {rid} violates predicate schema"
                    break
                # registered-entity endpoints (knowledge graph) must exist
                if r.object_kind == "term" and not terminology.exists(r.object_id):
                    ok, detail = False, f"relation {rid} object term not registered"
                    break
                if r.object_kind == "taxon" and not taxonomy.exists(r.object_id):
                    ok, detail = False, f"relation {rid} object taxon not registered"
                    break
                if r.subject_kind == "concept" and not concepts.exists(r.subject_id):
                    ok, detail = False, f"relation {rid} subject concept not registered"
                    break
            report.add("relationship_integrity", ok, detail)
        except Exception as exc:
            report.add("relationship_integrity", False, f"error: {exc}")

        # 5. registry integrity (latest snapshot matches current version + counts)
        try:
            latest = registry.latest()
            counts_ok = (latest.n_terms == len(terminology.list_terms())
                         and latest.n_concepts == len(concepts.list_concepts())
                         and latest.n_taxonomy_nodes == len(taxonomy.list_nodes())
                         and latest.n_relationships == len(relationships.list_relations()))
            report.add("registry_integrity", bool(latest.version == version and counts_ok),
                       f"latest_version={latest.version} version={version} counts_ok={counts_ok}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 6. lineage integrity
        try:
            ok = bool(head_lineage_id) and lineage_tracker.verify_chain(head_lineage_id)
            report.add("lineage_integrity", ok, f"head={head_lineage_id} verified={ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 7. audit integrity
        try:
            ok = audit_log.verify()
            report.add("audit_integrity", ok, f"chain_verified={ok} events={len(audit_log)}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise KnowledgeValidationError(f"knowledge validation failed: {names}")
