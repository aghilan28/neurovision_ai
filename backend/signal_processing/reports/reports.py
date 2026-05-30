"""Signal-processing report builders (reproducible; version-tagged).

Each report is a plain JSON-able dict, deterministic for a given processed-asset /
registry state (no wall-clock, no randomness). Mirrors the EEG-foundation report
style.
"""

from __future__ import annotations

from typing import Any

from ..version import SIGNAL_REPORT_VERSION, SIGNAL_PROCESSING_VERSION


def _header(report_type: str, asset: Any) -> dict:
    return {
        "report_type": report_type,
        "signal_report_version": SIGNAL_REPORT_VERSION,
        "signal_processing_version": SIGNAL_PROCESSING_VERSION,
        "processed_id": asset.processed_id,
        "eeg_asset_id": asset.eeg_asset_id,
        "case_id": asset.case_id,
        "patient_id": asset.patient_id,
        "processed_version": asset.version.version,
    }


def build_quality_report(asset: Any) -> dict:
    """Quality of the processed signal + the before/after quality history."""
    return {
        **_header("signal_quality", asset),
        "quality": asset.quality.to_dict(),
        "quality_history": asset.quality_history.to_dict(),
    }


def build_artifact_report(asset: Any) -> dict:
    """All detected artifacts + which were addressed."""
    return {
        **_header("signal_artifact", asset),
        "n_artifacts": len(asset.artifacts),
        "artifacts": [a.to_dict() for a in asset.artifacts],
        "artifact_history": asset.artifact_history.to_dict(),
    }


def build_filtering_report(asset: Any) -> dict:
    """The filter configurations applied (deterministic, reproducible)."""
    return {
        **_header("signal_filtering", asset),
        "filter_configs": [f.to_dict() for f in asset.processing.filter_configs],
        "filter_steps": [s.to_dict() for s in asset.processing.steps
                         if s.operation in {"bandpass", "highpass", "lowpass", "notch", "reference"}],
    }


def build_processing_report(asset: Any) -> dict:
    """The full ordered processing pipeline (raw -> clean)."""
    return {
        **_header("signal_processing", asset),
        "processing": asset.processing.to_dict(),
        "removal_methods": [m.value for m in asset.processing.removal_methods],
        "metadata": asset.metadata.to_dict(),
        "raw_signal": asset.raw_signal.to_dict(),
        "processed_signal": asset.processed_signal.to_dict(),
    }


def build_audit_report(asset: Any, audit_log: Any) -> dict:
    """The immutable, tamper-evident audit trail for the processed asset."""
    return {
        **_header("signal_audit", asset),
        "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(),
        "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_lineage_report(asset: Any, lineage_tracker: Any) -> dict:
    """The lineage chain (Patient -> Case -> EEG -> Processed) for the asset."""
    chain = lineage_tracker.chain(asset.lineage_id) if asset.lineage_id else []
    return {
        **_header("signal_lineage", asset),
        "lineage_id": asset.lineage_id,
        "chain_verified": lineage_tracker.verify_chain(asset.lineage_id) if asset.lineage_id else False,
        "chain_length": len(chain),
        "chain_kinds": [r.kind for r in chain],
        "chain": [r.to_dict() for r in chain],
    }


def build_registry_report(registry: Any) -> dict:
    """A registry-wide report of all registered processed assets."""
    return {
        "report_type": "signal_registry",
        "signal_report_version": SIGNAL_REPORT_VERSION,
        "signal_processing_version": SIGNAL_PROCESSING_VERSION,
        "n_assets": len(registry.list_assets()),
        "asset_ids": registry.list_assets(),
        "registry": registry.to_dict(),
    }
