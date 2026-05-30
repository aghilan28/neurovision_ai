"""External EEG dataset integration framework (P4-C).

Connectors for **TUH EEG**, **CHB-MIT**, and **Temple EEG** that *discover*,
*validate*, and *register* a dataset from a locally-provided **manifest** — they
never download data and never require internet access. A manifest is a plain dict
(or a local JSON file the caller already has) describing the dataset's structure;
the connector normalizes it into a ``DatasetRecord`` (with no numeric arrays — the
external recordings are not materialized here).

This is the integration *framework*: it lets the platform register and track external
datasets deterministically and auditable, so a later phase can attach the real data
behind the same contract.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import DatasetRecord, DatasetSource, DatasetStatus

# Required manifest fields per connector (the closed contract for a registered dataset).
_REQUIRED = ("name", "n_recordings", "patients", "channels", "sampling_frequency")


@dataclass(frozen=True)
class ConnectorSpec:
    source: DatasetSource
    display_name: str
    modality: str = "scalp_eeg"


CONNECTOR_SPECS: dict[DatasetSource, ConnectorSpec] = {
    DatasetSource.TUH_EEG: ConnectorSpec(DatasetSource.TUH_EEG, "Temple University Hospital EEG Corpus"),
    DatasetSource.CHB_MIT: ConnectorSpec(DatasetSource.CHB_MIT, "CHB-MIT Scalp EEG Database"),
    DatasetSource.TEMPLE_EEG: ConnectorSpec(DatasetSource.TEMPLE_EEG, "Temple University EEG (Temple)"),
}


class DatasetConnectorError(ValueError):
    """Raised on a malformed dataset manifest (registration is rejected)."""


class ExternalDatasetConnector:
    """Discovers + validates + registers an external dataset from a local manifest."""

    def __init__(self, source: DatasetSource):
        if source not in CONNECTOR_SPECS:
            raise DatasetConnectorError(f"no connector for source {source!r}")
        self.source = source
        self.spec = CONNECTOR_SPECS[source]

    def discover(self, manifest_or_path) -> dict:
        """Load a manifest from a dict or a local JSON path (no network)."""
        if isinstance(manifest_or_path, dict):
            return dict(manifest_or_path)
        path = str(manifest_or_path)
        if not os.path.exists(path):
            raise DatasetConnectorError(f"manifest path does not exist: {path}")
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def validate(self, manifest: dict) -> tuple[bool, list]:
        missing = [k for k in _REQUIRED if k not in manifest]
        problems = list(missing)
        if "patients" in manifest and not isinstance(manifest["patients"], (list, tuple)):
            problems.append("patients must be a list")
        if "n_recordings" in manifest and not isinstance(manifest["n_recordings"], int):
            problems.append("n_recordings must be an int")
        return (len(problems) == 0), problems

    def build_record(self, manifest_or_path, *, dataset_key: str) -> DatasetRecord:
        """Validate a manifest and produce a registered (or quarantined) DatasetRecord."""
        from ..identity import mint_identity

        manifest = self.discover(manifest_or_path)
        ok, problems = self.validate(manifest)
        manifest_fp = hash_obj(_canonical_manifest(manifest))
        identity = mint_identity("dataset", {
            "source": self.source.value, "dataset_key": dataset_key, "content_key": manifest_fp})
        patients = tuple(str(p) for p in manifest.get("patients", []))
        class_labels = tuple(int(c) for c in manifest.get("class_labels", []))
        status = DatasetStatus.REGISTERED if ok else DatasetStatus.QUARANTINED
        source_meta = {
            "display_name": self.spec.display_name, "modality": self.spec.modality,
            "channels": list(manifest.get("channels", [])),
            "sampling_frequency": manifest.get("sampling_frequency"),
            "path": manifest.get("path"), "validation_problems": problems,
            "downloaded": False,
        }
        return DatasetRecord(
            dataset_id=identity.id, source=self.source, name=str(manifest.get("name", self.spec.display_name)),
            n_samples=int(manifest.get("n_recordings", 0)), n_features=0, feature_names=(),
            class_labels=class_labels, class_distribution={}, patient_ids=patients,
            feature_asset_ids=(), split=None, data_fingerprint=manifest_fp, status=status,
            source_metadata=source_meta)


def _canonical_manifest(manifest: dict) -> dict:
    out = {}
    for k in sorted(manifest):
        v = manifest[k]
        out[k] = list(v) if isinstance(v, (list, tuple)) else v
    return out
