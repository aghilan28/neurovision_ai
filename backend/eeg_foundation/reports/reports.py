"""EEG report builders (reproducible; version-tagged).

Each report is a plain JSON-able dict, deterministic for a given asset/registry
state (no wall-clock, no randomness). Mirrors the clinical-case report style.
"""

from __future__ import annotations

from typing import Any

from ..version import EEG_REPORT_VERSION, EEG_FOUNDATION_VERSION


def _header(report_type: str, asset: Any) -> dict:
    return {
        "report_type": report_type,
        "eeg_report_version": EEG_REPORT_VERSION,
        "eeg_foundation_version": EEG_FOUNDATION_VERSION,
        "asset_id": asset.asset_id,
        "case_id": asset.case_id,
        "patient_id": asset.patient_id,
        "asset_version": asset.version.version,
    }


def build_eeg_summary_report(asset: Any) -> dict:
    """High-level summary of a registered EEG asset."""
    return {
        **_header("eeg_summary", asset),
        "status": asset.status.value,
        "eeg_format": asset.eeg_format.value,
        "owner": asset.owner,
        "created_at": asset.created_at,
        "original_filename": asset.source.original_filename,
        "file_size_bytes": asset.source.file_size_bytes,
        "n_channels": asset.channel_set.count,
        "sampling_frequency": asset.metadata.sampling_frequency,
        "duration_seconds": asset.metadata.duration_seconds,
        "n_annotations": asset.metadata.n_annotations,
        "validation_ok": asset.validation.ok,
        "lineage_id": asset.lineage_id,
        "audit_head": asset.audit_head,
    }


def build_eeg_metadata_report(asset: Any) -> dict:
    """The full normalized metadata for an asset."""
    return {
        **_header("eeg_metadata", asset),
        "metadata": asset.metadata.to_dict(),
        "channel_set": asset.channel_set.to_dict(),
        "annotations": [a.to_dict() for a in asset.annotations],
        "source": asset.source.to_dict(),
    }


def build_eeg_validation_report(asset: Any) -> dict:
    """The structured validation findings for an asset."""
    return {
        **_header("eeg_validation", asset),
        "validation": asset.validation.to_dict(),
    }


def build_eeg_audit_report(asset: Any, audit_log: Any) -> dict:
    """The immutable, tamper-evident audit trail for an asset."""
    return {
        **_header("eeg_audit", asset),
        "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(),
        "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_eeg_lineage_report(asset: Any, lineage_tracker: Any) -> dict:
    """The lineage chain (Patient -> Case -> EEG) for an asset."""
    chain = lineage_tracker.chain(asset.lineage_id) if asset.lineage_id else []
    return {
        **_header("eeg_lineage", asset),
        "lineage_id": asset.lineage_id,
        "chain_verified": lineage_tracker.verify_chain(asset.lineage_id) if asset.lineage_id else False,
        "chain_length": len(chain),
        "chain_kinds": [r.kind for r in chain],
        "chain": [r.to_dict() for r in chain],
    }


def build_eeg_registry_report(registry: Any) -> dict:
    """A registry-wide report of all registered EEG assets."""
    return {
        "report_type": "eeg_registry",
        "eeg_report_version": EEG_REPORT_VERSION,
        "eeg_foundation_version": EEG_FOUNDATION_VERSION,
        "n_assets": len(registry.list_assets()),
        "asset_ids": registry.list_assets(),
        "registry": registry.to_dict(),
    }
