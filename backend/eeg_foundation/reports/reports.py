"""EEG report builders (reproducible; version-tagged) (Productization P1).

Every report is a deterministic projection of an EEG asset + registry/audit/lineage
state. Reports add no new truth.
"""

from __future__ import annotations

from typing import Any

from ..version import EEG_REPORT_VERSION, EEG_FOUNDATION_VERSION


def _header(report_type: str, eeg_id: str = "") -> dict:
    return {"report_type": report_type, "eeg_report_version": EEG_REPORT_VERSION,
            "eeg_foundation_version": EEG_FOUNDATION_VERSION, "eeg_id": eeg_id}


def build_eeg_summary_report(record) -> dict:
    return {**_header("eeg_summary", record.eeg_id), "format": record.fmt,
            "status": record.status, "valid": record.valid,
            "case_id": record.case_id, "patient_id": record.patient_id,
            "n_channels": record.metadata.n_channels,
            "n_signal_channels": record.metadata.n_signal_channels,
            "sampling_frequency": record.metadata.sampling_frequency,
            "duration_seconds": record.metadata.duration_seconds,
            "annotation_count": record.metadata.annotation_count,
            "version": record.version, "lineage_id": record.lineage_id}


def build_eeg_validation_report(record) -> dict:
    return {**_header("eeg_validation", record.eeg_id), "valid": record.valid,
            "validation": record.validation_summary}


def build_eeg_metadata_report(record) -> dict:
    return {**_header("eeg_metadata", record.eeg_id), "metadata": record.metadata.to_dict()}


def build_eeg_registry_report(registry: Any) -> dict:
    return {**_header("eeg_registry"), "registry": registry.to_dict()}


def build_eeg_audit_report(audit_log: Any) -> dict:
    return {**_header("eeg_audit"), "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_eeg_lineage_report(record, lineage_tracker: Any) -> dict:
    verified = lineage_tracker.verify_chain(record.lineage_id) if record.lineage_id else False
    chain = ([r.kind for r in lineage_tracker.chain(record.lineage_id)]
             if record.lineage_id and verified else [])
    return {**_header("eeg_lineage", record.eeg_id), "lineage_id": record.lineage_id,
            "lineage_verified": verified, "chain_kinds": chain,
            "reaches_patient": "patient" in chain}
