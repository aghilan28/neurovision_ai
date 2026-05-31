"""``backend/dataset_integration/inventory`` — dataset inventory system (DRP1-C).

Inventories external EEG corpora from **local manifests** (no automatic download). Ships a
built-in catalog of the mandatory corpora (TUH EEG, CHB-MIT, Temple/TUSZ, Siena Scalp, Bonn)
as accurate, public *metadata* manifests, and builds a normalized inventory record (name /
version / location / format / license / source / size / channels / sampling / metadata
completeness / status). Any future EEG dataset is inventoried by supplying its own manifest.
"""

from __future__ import annotations

import json
import os

from ..models.domain import (
    DatasetFormat, DatasetInventoryRecord, EegDatasetSource, InventoryStatus,
)
from ..identity import mint_identity

MANIFEST_DIR = os.path.join(os.path.dirname(__file__), "manifests")

# The mandatory built-in catalog (source -> manifest filename).
BUILTIN_CATALOG = {
    EegDatasetSource.TUH_EEG: "tuh_eeg.json",
    EegDatasetSource.CHB_MIT: "chb_mit.json",
    EegDatasetSource.TEMPLE_EEG: "temple_eeg.json",
    EegDatasetSource.SIENA_SCALP: "siena_scalp.json",
    EegDatasetSource.BONN: "bonn.json",
}

# Fields whose presence defines a fully-described corpus (drives completeness scoring).
_COMPLETENESS_FIELDS = ("name", "source", "version", "format", "location", "n_recordings",
                        "patients", "channels", "sampling_frequency", "size", "governance")


class InventoryError(ValueError):
    """Raised on a manifest that cannot be inventoried."""


def load_manifest(manifest_or_path) -> dict:
    """Load a manifest from a dict or a local JSON path (no network)."""
    if isinstance(manifest_or_path, dict):
        return dict(manifest_or_path)
    path = str(manifest_or_path)
    if not os.path.exists(path):
        raise InventoryError(f"manifest path does not exist: {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def builtin_manifest(source: EegDatasetSource) -> dict:
    if source not in BUILTIN_CATALOG:
        raise InventoryError(f"no built-in manifest for {source!r}")
    return load_manifest(os.path.join(MANIFEST_DIR, BUILTIN_CATALOG[source]))


def list_builtin_manifests() -> dict:
    return {src: builtin_manifest(src) for src in BUILTIN_CATALOG}


def metadata_completeness(manifest: dict) -> float:
    present = sum(1 for f in _COMPLETENESS_FIELDS
                  if f in manifest and manifest[f] not in (None, "", [], {}))
    return round(present / len(_COMPLETENESS_FIELDS), 6)


def _coerce_source(value) -> EegDatasetSource:
    try:
        return EegDatasetSource(str(value))
    except ValueError:
        return EegDatasetSource.OTHER


def _coerce_format(value) -> DatasetFormat:
    try:
        return DatasetFormat(str(value))
    except ValueError:
        return DatasetFormat.OTHER


def build_inventory_record(manifest: dict) -> DatasetInventoryRecord:
    """Normalize a manifest into a deterministic inventory record (inventory only)."""
    source = _coerce_source(manifest.get("source"))
    completeness = metadata_completeness(manifest)
    inv_id = mint_identity("dataset_source", {"source": source.value}).id.replace(
        "dataset_source+", "inventory+")
    # status: inventoried if the minimum descriptive fields are present, else quarantined
    minimal = all(k in manifest for k in ("name", "source", "n_recordings"))
    status = InventoryStatus.INVENTORIED if minimal else InventoryStatus.QUARANTINED
    return DatasetInventoryRecord(
        inventory_id=inv_id, source=source, name=str(manifest.get("name", "")),
        version_label=str(manifest.get("version", "")), location=str(manifest.get("location", "")),
        format=_coerce_format(manifest.get("format")),
        license_name=str((manifest.get("governance") or {}).get("license_name", "")),
        size=dict(manifest.get("size", {})), channels=tuple(manifest.get("channels", [])),
        sampling_frequency=(float(manifest["sampling_frequency"])
                            if manifest.get("sampling_frequency") is not None else None),
        n_recordings=int(manifest.get("n_recordings", 0) or 0),
        n_patients=int(manifest.get("n_patients", len(manifest.get("patients", []))) or 0),
        metadata_completeness=completeness, status=status, downloaded=False)


def build_full_inventory() -> list:
    """Inventory every built-in corpus (deterministic order)."""
    return [build_inventory_record(builtin_manifest(src)) for src in BUILTIN_CATALOG]


__all__ = [
    "MANIFEST_DIR", "BUILTIN_CATALOG", "InventoryError", "load_manifest", "builtin_manifest",
    "list_builtin_manifests", "metadata_completeness", "build_inventory_record",
    "build_full_inventory",
]
