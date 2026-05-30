"""Knowledge report builders (reproducible; version-tagged)."""

from __future__ import annotations

from typing import Any

from ..version import KNOWLEDGE_REPORT_VERSION, CLINICAL_KNOWLEDGE_VERSION


def _header(report_type: str, version: str, head_lineage_id: str) -> dict:
    return {"report_type": report_type, "knowledge_report_version": KNOWLEDGE_REPORT_VERSION,
            "clinical_knowledge_version": CLINICAL_KNOWLEDGE_VERSION,
            "knowledge_version": version, "head_lineage_id": head_lineage_id}


def build_knowledge_summary_report(*, version, head_lineage_id, terminology, concepts,
                                   taxonomy, relationships) -> dict:
    return {
        **_header("knowledge_summary", version, head_lineage_id),
        "n_terms": len(terminology.list_terms()),
        "n_concepts": len(concepts.list_concepts()),
        "n_taxonomy_nodes": len(taxonomy.list_nodes()),
        "n_relationships": len(relationships.list_relations()),
    }


def build_terminology_report(*, version, head_lineage_id, terminology) -> dict:
    return {**_header("terminology", version, head_lineage_id), "terminology": terminology.to_dict()}


def build_concept_report(*, version, head_lineage_id, concepts) -> dict:
    return {**_header("concept", version, head_lineage_id), "concepts": concepts.to_dict()}


def build_taxonomy_report(*, version, head_lineage_id, taxonomy) -> dict:
    ok, detail = taxonomy.check_consistency()
    return {**_header("taxonomy", version, head_lineage_id),
            "consistent": ok, "detail": detail, "taxonomy": taxonomy.to_dict()}


def build_relationship_report(*, version, head_lineage_id, relationships) -> dict:
    return {**_header("relationship", version, head_lineage_id),
            "relationships": relationships.to_dict()}


def build_knowledge_validation_report(*, version, head_lineage_id, validation_report_dict) -> dict:
    return {**_header("knowledge_validation", version, head_lineage_id),
            "validation": validation_report_dict}
