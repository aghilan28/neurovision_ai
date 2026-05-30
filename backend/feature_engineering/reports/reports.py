"""Feature report builders (reproducible; version-tagged).

Each report is a plain JSON-able dict, deterministic for a given feature-asset /
registry state (no wall-clock, no randomness). Mirrors the platform report style.
"""

from __future__ import annotations

from typing import Any, Optional

from ..models.domain import FeatureFamily
from ..version import FEATURE_REPORT_VERSION, FEATURE_ENGINEERING_VERSION


def _header(report_type: str, asset: Any) -> dict:
    return {
        "report_type": report_type,
        "feature_report_version": FEATURE_REPORT_VERSION,
        "feature_engineering_version": FEATURE_ENGINEERING_VERSION,
        "feature_asset_id": asset.feature_asset_id,
        "processed_id": asset.processed_id,
        "eeg_asset_id": asset.eeg_asset_id,
        "case_id": asset.case_id,
        "patient_id": asset.patient_id,
        "feature_version": asset.version.version,
    }


def _family_vectors(asset: Any, family: FeatureFamily) -> list:
    return [v.to_dict() for v in asset.vectors if v.family == family]


def build_frequency_report(asset: Any) -> dict:
    return {**_header("feature_frequency", asset),
            "vectors": _family_vectors(asset, FeatureFamily.FREQUENCY)}


def build_temporal_report(asset: Any) -> dict:
    return {**_header("feature_temporal", asset),
            "vectors": _family_vectors(asset, FeatureFamily.TEMPORAL)}


def build_connectivity_report(asset: Any) -> dict:
    return {**_header("feature_connectivity", asset),
            "vectors": _family_vectors(asset, FeatureFamily.CONNECTIVITY)}


def build_spectral_report(asset: Any) -> dict:
    return {**_header("feature_spectral", asset),
            "vectors": _family_vectors(asset, FeatureFamily.SPECTRAL)}


def build_topography_report(asset: Any) -> dict:
    return {**_header("feature_topography", asset),
            "vectors": _family_vectors(asset, FeatureFamily.TOPOGRAPHY)}


def build_audit_report(asset: Any, audit_log: Any) -> dict:
    return {
        **_header("feature_audit", asset),
        "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(),
        "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_lineage_report(asset: Any, lineage_tracker: Any) -> dict:
    chain = lineage_tracker.chain(asset.lineage_id) if asset.lineage_id else []
    return {
        **_header("feature_lineage", asset),
        "lineage_id": asset.lineage_id,
        "chain_verified": lineage_tracker.verify_chain(asset.lineage_id) if asset.lineage_id else False,
        "chain_length": len(chain),
        "chain_kinds": [r.kind for r in chain],
        "chain": [r.to_dict() for r in chain],
    }


def build_validation_report(asset: Any, integrity_report: Optional[Any] = None) -> dict:
    out = {**_header("feature_validation", asset),
           "content_validation": asset.validation.to_dict()}
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(asset.validation.ok and integrity_report.ok)
    else:
        out["ok"] = bool(asset.validation.ok)
    return out


def build_registry_report(registry: Any) -> dict:
    return {
        "report_type": "feature_registry",
        "feature_report_version": FEATURE_REPORT_VERSION,
        "feature_engineering_version": FEATURE_ENGINEERING_VERSION,
        "n_assets": len(registry.list_assets()),
        "asset_ids": registry.list_assets(),
        "registry": registry.to_dict(),
    }
