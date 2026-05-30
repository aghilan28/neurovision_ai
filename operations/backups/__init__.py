"""``operations/backups`` — backup foundation (P8-H).

Backs up the operational state needed to recover the platform: the backend **registry**
(serialized), the **configuration** (redacted — secrets are never backed up), and the
content-addressed **artifacts** (raw/processed/feature/upload stores). Each backup writes
a checksummed manifest so a restore can be verified bit-for-bit.

No cloud: backups are written to a local destination directory (a mounted/persistent
volume in a real deployment).
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Optional

from ..util import canonical_json, file_sha256, fingerprint
from ..version import DETERMINISTIC_EPOCH, OPERATIONS_BACKUP_VERSION


@dataclass(frozen=True)
class BackupComponent:
    name: str
    path: str               # relative to the backup root
    sha256: str
    bytes: int

    def to_dict(self) -> dict:
        return {"name": self.name, "path": self.path, "sha256": self.sha256, "bytes": self.bytes}


@dataclass(frozen=True)
class BackupManifest:
    backup_id: str
    created_at: str
    components: tuple
    artifacts: tuple
    signature: str

    def to_dict(self) -> dict:
        return {
            "backup_version": OPERATIONS_BACKUP_VERSION, "backup_id": self.backup_id,
            "created_at": self.created_at,
            "components": [c.to_dict() for c in self.components],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "signature": self.signature,
        }


class BackupManager:
    """Creates verifiable, checksummed backups of operational state."""

    def __init__(self, *, created_at: str = DETERMINISTIC_EPOCH):
        self.created_at = created_at

    def backup(self, dest_dir: str, *, registry=None, config=None,
               artifact_roots: Optional[dict] = None) -> BackupManifest:
        os.makedirs(dest_dir, exist_ok=True)
        components: list[BackupComponent] = []

        if registry is not None:
            components.append(self._write_json(dest_dir, "registry", "registry.json",
                                               registry.to_dict()))
        if config is not None:
            # secrets are NEVER backed up (config is redacted)
            components.append(self._write_json(dest_dir, "config", "config.json",
                                               config.to_dict(redact=True)))

        artifacts: list[BackupComponent] = []
        for label, root in sorted((artifact_roots or {}).items()):
            if not root or not os.path.isdir(root):
                continue
            for rel, abspath in self._walk(root):
                stored_rel = os.path.join("artifacts", label, rel)
                stored_abs = os.path.join(dest_dir, stored_rel)
                os.makedirs(os.path.dirname(stored_abs), exist_ok=True)
                shutil.copy2(abspath, stored_abs)
                artifacts.append(BackupComponent(
                    f"{label}/{rel}", stored_rel.replace(os.sep, "/"),
                    file_sha256(stored_abs), os.path.getsize(stored_abs)))

        backup_id = "backup+" + fingerprint({
            "components": [c.to_dict() for c in components],
            "artifacts": [a.to_dict() for a in artifacts]})
        signature = fingerprint({"id": backup_id,
                                 "components": [c.sha256 for c in components],
                                 "artifacts": [a.sha256 for a in artifacts]})
        manifest = BackupManifest(backup_id, self.created_at, tuple(components),
                                  tuple(artifacts), signature)
        with open(os.path.join(dest_dir, "manifest.json"), "w", encoding="utf-8") as fh:
            fh.write(canonical_json(manifest.to_dict()))
        return manifest

    # --- helpers --------------------------------------------------------------
    def _write_json(self, dest_dir: str, name: str, rel: str, payload: dict) -> BackupComponent:
        path = os.path.join(dest_dir, rel)
        os.makedirs(os.path.dirname(path) or dest_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(canonical_json(payload))
        return BackupComponent(name, rel, file_sha256(path), os.path.getsize(path))

    @staticmethod
    def _walk(root: str):
        for dirpath, _dirs, files in os.walk(root):
            for f in sorted(files):
                abspath = os.path.join(dirpath, f)
                yield os.path.relpath(abspath, root).replace(os.sep, "/"), abspath


def build_backup_report(manifest: BackupManifest) -> dict:
    return {
        "report_type": "backup", "backup_version": OPERATIONS_BACKUP_VERSION,
        "backup_id": manifest.backup_id, "signature": manifest.signature,
        "n_components": len(manifest.components), "n_artifacts": len(manifest.artifacts),
        "total_bytes": sum(a.bytes for a in manifest.artifacts) + sum(c.bytes for c in manifest.components),
    }


__all__ = ["BackupManager", "BackupManifest", "BackupComponent", "build_backup_report"]
