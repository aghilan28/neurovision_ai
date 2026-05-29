"""``datasets.versioning`` — checksums, manifests, versions, audits.

Guarantees there are **no silent dataset modifications** (Project directive). The
mechanism is content-addressing end to end:

* **Checksums** (:mod:`datasets.versioning.checksums`) — SHA-256 of file bytes.
* **Manifests** (:mod:`datasets.versioning.manifest_builder`) — the content-addressed
  membership of a dataset, with an order-independent fingerprint.
* **Versions** (:mod:`datasets.versioning.version_chain`) — an append-only chain of
  fingerprinted snapshots with change tracking (diffs) between them.
* **Audits** (:mod:`datasets.versioning.audit`) — re-verify that a dataset version
  still matches its manifest and its records (reproducibility tracking).
"""

from __future__ import annotations

from datasets.versioning.audit import AuditReport, audit_manifest, verify_dataset_version
from datasets.versioning.checksums import checksum_bytes, checksum_file, verify_checksum
from datasets.versioning.manifest_builder import build_manifest
from datasets.versioning.version_chain import (
    ManifestDiff,
    VersionChainError,
    VersionedDataset,
    diff_manifests,
)

__all__ = [
    "AuditReport",
    "ManifestDiff",
    "VersionChainError",
    "VersionedDataset",
    "audit_manifest",
    "build_manifest",
    "checksum_bytes",
    "checksum_file",
    "diff_manifests",
    "verify_checksum",
    "verify_dataset_version",
]
