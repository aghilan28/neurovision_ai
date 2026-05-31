"""``backend/dataset_acquisition/reports`` — deterministic real-dataset reports (T1-I).

Nine reports: Acquisition, Validation, Inventory, Label, Metadata, Readiness, Audit,
Lineage, and Dataset Summary. Every report is a pure function of the (already
deterministic) records, so it reproduces byte-for-byte for a given local dataset state.
"""

from __future__ import annotations

from typing import Optional

from ..version import ACQUISITION_REPORT_VERSION


def _header(report_type: str) -> dict:
    return {"report_type": report_type, "acquisition_report_version": ACQUISITION_REPORT_VERSION}


def build_acquisition_report(records: list) -> dict:
    return {**_header("acquisition"), "n_sources": len(records),
            "acquisitions": [r.to_dict() for r in records]}


def build_validation_report(record) -> dict:
    return {**_header("validation"), "validation": record.to_dict()}


def build_inventory_report(record) -> dict:
    return {**_header("inventory"), "inventory": record.to_dict()}


def build_label_report(record) -> dict:
    return {**_header("label"), "label_verification": record.to_dict()}


def build_metadata_report(result) -> dict:
    """Per-recording normalized metadata (channels / sampling / duration / format)."""
    recordings = sorted(result.recordings, key=lambda r: r.recording_id)
    return {**_header("metadata"), "source": result.source.value,
            "n_recordings": len(recordings),
            "recordings": [{"recording_id": r.recording_id, "patient_id": r.patient_id,
                            "session_id": r.session_id, "format": r.fmt.value,
                            "sampling_frequency": round(r.sampling_frequency, 6),
                            "duration_seconds": round(r.duration_seconds, 6),
                            "n_channels": r.n_channels, "n_samples": r.n_samples,
                            "channel_labels": list(r.channel_labels),
                            "n_annotations": r.n_annotations} for r in recordings]}


def build_readiness_report(record) -> dict:
    return {**_header("readiness"), "readiness": record.to_dict()}


def build_audit_report(audit_log, *, subject: str) -> dict:
    return {**_header("audit"), "subject": subject, "audit_head": audit_log.head,
            "chain_verified": audit_log.verify(), "n_events": len(audit_log),
            "events": [e.to_dict() for e in audit_log.events()]}


def build_lineage_report(lineage_tracker, lineage_id: Optional[str]) -> dict:
    chain = lineage_tracker.chain(lineage_id) if lineage_id else []
    return {**_header("lineage"), "lineage_id": lineage_id,
            "chain_verified": lineage_tracker.verify_chain(lineage_id) if lineage_id else False,
            "chain_length": len(chain),
            "chain_kinds": sorted({r.kind for r in chain}),
            "chain": [r.to_dict() for r in chain]}


def build_dataset_summary_report(record) -> dict:
    return {**_header("dataset_summary"), "dataset_id": record.dataset_id,
            "source": record.source.value, "name": record.name,
            "local_root": record.local_root,
            "availability_state": record.availability_state.value,
            "n_patients": record.n_patients, "n_recordings": record.n_recordings,
            "n_labels": record.n_labels, "dataset": record.to_dict()}


__all__ = [
    "build_acquisition_report", "build_validation_report", "build_inventory_report",
    "build_label_report", "build_metadata_report", "build_readiness_report",
    "build_audit_report", "build_lineage_report", "build_dataset_summary_report",
]
