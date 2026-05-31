"""``backend/dataset_integration/registration`` — registration helpers (DRP1-D).

Deterministic helpers for canonicalizing a manifest, computing its content fingerprint,
generating a normalized manifest, and **delegating to the existing model-foundation
connector framework** for the sources it supports (TUH / CHB-MIT / Temple) — so registration
integrates with, rather than duplicates, the platform dataset connectors. Siena / Bonn /
other corpora are validated by this subsystem directly (no model-foundation connector exists).
"""

from __future__ import annotations

from typing import Optional

from ml.provenance import hash_obj           # allowed: backend -> ml

from ..models.domain import EegDatasetSource

# my source vocabulary -> model-foundation DatasetSource value (only where a connector exists)
_MF_CONNECTOR_SOURCES = {
    EegDatasetSource.TUH_EEG: "tuh_eeg",
    EegDatasetSource.CHB_MIT: "chb_mit",
    EegDatasetSource.TEMPLE_EEG: "temple_eeg",
}


def canonical_manifest(manifest: dict) -> dict:
    out = {}
    for k in sorted(manifest):
        v = manifest[k]
        out[k] = list(v) if isinstance(v, (list, tuple)) else v
    return out


def manifest_fingerprint(manifest: dict) -> str:
    return hash_obj(canonical_manifest(manifest))


def delegate_to_model_foundation(source: EegDatasetSource, manifest: dict, *,
                                 dataset_key: str) -> Optional[str]:
    """If model-foundation has a connector for ``source``, register there and return its
    ``DatasetRecord.dataset_id`` (integration). Otherwise return ``None``."""
    mf_value = _MF_CONNECTOR_SOURCES.get(source)
    if mf_value is None:
        return None
    try:
        from backend.model_foundation import ExternalDatasetConnector, DatasetSource
        connector = ExternalDatasetConnector(DatasetSource(mf_value))
        record = connector.build_record(manifest, dataset_key=dataset_key)
        return record.dataset_id
    except Exception:
        # delegation is best-effort integration; failure never blocks this subsystem
        return None


def has_model_foundation_connector(source: EegDatasetSource) -> bool:
    return source in _MF_CONNECTOR_SOURCES


__all__ = ["canonical_manifest", "manifest_fingerprint", "delegate_to_model_foundation",
           "has_model_foundation_connector"]
