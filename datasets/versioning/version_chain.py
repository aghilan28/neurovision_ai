"""Dataset version chain and change tracking.

A :class:`VersionedDataset` is an append-only chain of fingerprinted
:class:`~datasets.schemas.dataset_version.DatasetVersion` snapshots. Adding a
version records its parent and the manifest fingerprint it certifies; the chain
exposes the change (diff) between consecutive manifests so every modification is
explicit and auditable (no silent changes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datasets import DATA_FOUNDATION_VERSION
from datasets.schemas.dataset_version import DatasetVersion
from datasets.schemas.manifest import DatasetManifest


class VersionChainError(ValueError):
    """Raised on an invalid version-chain operation."""


@dataclass(frozen=True, slots=True)
class ManifestDiff:
    """The change between two manifests, tracked by content-addressed file ids."""

    added_file_ids: tuple[str, ...]
    removed_file_ids: tuple[str, ...]
    added_patient_ids: tuple[str, ...]
    removed_patient_ids: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not (self.added_file_ids or self.removed_file_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_file_ids": list(self.added_file_ids),
            "removed_file_ids": list(self.removed_file_ids),
            "added_patient_ids": list(self.added_patient_ids),
            "removed_patient_ids": list(self.removed_patient_ids),
        }


def diff_manifests(old: DatasetManifest | None, new: DatasetManifest) -> ManifestDiff:
    """Compute the membership change from ``old`` to ``new`` (``old`` may be ``None``)."""
    old_files = {e.file_id for e in old.entries} if old else set()
    new_files = {e.file_id for e in new.entries}
    old_patients = set(old.patient_ids) if old else set()
    new_patients = set(new.patient_ids)
    return ManifestDiff(
        added_file_ids=tuple(sorted(new_files - old_files)),
        removed_file_ids=tuple(sorted(old_files - new_files)),
        added_patient_ids=tuple(sorted(new_patients - old_patients)),
        removed_patient_ids=tuple(sorted(old_patients - new_patients)),
    )


class VersionedDataset:
    """Append-only version chain for a single dataset."""

    def __init__(self, dataset_id: str) -> None:
        self.dataset_id = dataset_id
        self._versions: list[DatasetVersion] = []
        self._manifests: dict[str, DatasetManifest] = {}

    def __len__(self) -> int:
        return len(self._versions)

    @property
    def latest(self) -> DatasetVersion | None:
        return self._versions[-1] if self._versions else None

    def commit(
        self,
        manifest: DatasetManifest,
        *,
        change_summary: str = "",
        created_at: str | None = None,
        allow_noop: bool = False,
    ) -> tuple[DatasetVersion, ManifestDiff]:
        """Commit a manifest as the next version; returns ``(version, diff)``.

        Raises if the manifest's ``dataset_id`` does not match the chain, or if the
        new manifest is identical to the latest one (a no-op) unless ``allow_noop``.
        """
        if manifest.dataset_id != self.dataset_id:
            raise VersionChainError(
                f"manifest dataset {manifest.dataset_id!r} != chain {self.dataset_id!r}"
            )

        previous = self.latest
        previous_manifest = self._manifests.get(previous.version) if previous else None
        diff = diff_manifests(previous_manifest, manifest)

        if previous is not None and previous.manifest_fingerprint == manifest.content_fingerprint and not allow_noop:
            raise VersionChainError(
                "manifest is identical to the latest version (no change to commit)"
            )

        version = DatasetVersion(
            dataset_id=self.dataset_id,
            version=manifest.version,
            manifest_fingerprint=manifest.content_fingerprint,
            data_foundation_version=manifest.data_foundation_version or DATA_FOUNDATION_VERSION,
            parent_version=previous.version if previous else None,
            record_count=manifest.record_count,
            patient_count=manifest.patient_count,
            change_summary=change_summary,
            created_at=created_at,
        )
        if any(v.version == version.version for v in self._versions):
            raise VersionChainError(f"version {version.version!r} already exists in the chain")

        self._versions.append(version)
        self._manifests[version.version] = manifest
        return version, diff

    def get_version(self, version: str) -> DatasetVersion:
        for v in self._versions:
            if v.version == version:
                return v
        raise VersionChainError(f"unknown version {version!r}")

    def get_manifest(self, version: str) -> DatasetManifest:
        try:
            return self._manifests[version]
        except KeyError as exc:
            raise VersionChainError(f"unknown version {version!r}") from exc

    def history(self) -> tuple[DatasetVersion, ...]:
        return tuple(self._versions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "versions": [v.to_dict() for v in self._versions],
            "manifests": {k: m.to_dict() for k, m in self._manifests.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VersionedDataset:
        chain = cls(data["dataset_id"])
        chain._versions = [DatasetVersion.from_dict(v) for v in data.get("versions", [])]
        chain._manifests = {
            k: DatasetManifest.from_dict(m) for k, m in data.get("manifests", {}).items()
        }
        return chain
