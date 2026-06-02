"""``backend/dataset_integration/reports`` — deterministic dataset reports (DRP1-J)."""

from __future__ import annotations

from typing import Optional

from ..version import DATASET_REPORT_VERSION


def _header(report_type: str) -> dict:
    return {"report_type": report_type, "dataset_report_version": DATASET_REPORT_VERSION}


def build_inventory_report(inventories: list) -> dict:
    return {**_header("inventory"), "n_datasets": len(inventories),
            "datasets": [i.to_dict() for i in inventories]}


def build_validation_report(record) -> dict:
    return {**_header("validation"), "validation": record.to_dict()}


def build_governance_report(record) -> dict:
    return {**_header("governance"), "governance": record.to_dict()}


def build_readiness_report(record) -> dict:
    return {**_header("readiness"), "readiness": record.to_dict()}


def build_registry_report(registry) -> dict:
    return {**_header("registry"), "n_records": registry.to_dict()["n_records"],
            "counts": registry.counts(), "orphans": registry.orphans(),
            "registry": registry.to_dict()}


def build_audit_report(audit_log, *, subject: str) -> dict:
    return {**_header("audit"), "subject": subject, "audit_head": audit_log.head,
            "chain_verified": audit_log.verify(), "n_events": len(audit_log),
            "events": [e.to_dict() for e in audit_log.events()]}


def build_lineage_report(lineage_tracker, lineage_id: Optional[str]) -> dict:
    chain = lineage_tracker.chain(lineage_id) if lineage_id else []
    return {**_header("lineage"), "lineage_id": lineage_id,
            "chain_verified": lineage_tracker.verify_chain(lineage_id) if lineage_id else False,
            "chain_length": len(chain), "chain_kinds": [r.kind for r in chain],
            "chain": [r.to_dict() for r in chain]}


def build_dataset_summary_report(record) -> dict:
    return {**_header("dataset_summary"), "dataset_id": record.dataset_id,
            "source": record.source.value, "status": record.status.value,
            "name": record.inventory.name, "n_recordings": record.inventory.n_recordings,
            "n_patients": record.inventory.n_patients,
            "model_foundation_dataset_id": record.model_foundation_dataset_id,
            "dataset": record.to_dict()}


__all__ = [
    "build_inventory_report", "build_validation_report", "build_governance_report",
    "build_readiness_report", "build_registry_report", "build_audit_report",
    "build_lineage_report", "build_dataset_summary_report",
]
