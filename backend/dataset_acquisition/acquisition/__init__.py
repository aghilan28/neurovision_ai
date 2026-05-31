"""``backend/dataset_acquisition/acquisition`` — Dataset Acquisition Program (T1-A).

Acquires the **minimal real subset** of an OPEN corpus on demand (PhysioNet over HTTPS)
into the local storage root, and reports the acquisition plan for every mandatory corpus.

Policy (directive): corpora that require an account or a signed data-use agreement
(``REGISTRATION_REQUIRED`` / ``RESTRICTED``) are **never auto-downloaded** — only their
acquisition plan is reported. Downloads never raise: a network/IO failure becomes a
structured ``AcquisitionItem`` state (``UNAVAILABLE`` / ``PARTIALLY_DOWNLOADED``).

Determinism (NR-9/NR-10): the acquisition *record* carries content checksums (a pure
function of the bytes) and a spec signature — never wall-clock timings or download
durations — so a re-run over the same local files reproduces the same record.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request

from ml.provenance import hash_obj, sha256_of_file  # allowed: backend -> ml

from ..models.domain import (
    AccessRequirement, AcquisitionItem, AcquisitionRecord, AcquisitionSourceSpec, AvailabilityState,
    DatasetSource,
)
from ..sources import all_specs, spec_for
from ..storage import DatasetStorageManager

_USER_AGENT = "neurovision-dataset-acquisition/1.0 (+research; urllib)"
_CHUNK = 1 << 20  # 1 MiB


class DownloadError(RuntimeError):
    """Raised internally on a failed download (always caught and turned into a state)."""


def _download(url: str, dest: str, *, timeout: float = 60.0,
              max_bytes: int | None = None) -> int:
    """Stream ``url`` to ``dest`` (atomic via .part); return bytes written. May raise."""
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    written = 0
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https only)
        with open(tmp, "wb") as fh:
            while True:
                chunk = resp.read(_CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if max_bytes is not None and written > max_bytes:
                    raise DownloadError(f"exceeded max_bytes={max_bytes}")
                fh.write(chunk)
    os.replace(tmp, dest)
    return written


def spec_signature(spec: AcquisitionSourceSpec) -> str:
    return hash_obj(spec.to_dict())


def acquire(spec: AcquisitionSourceSpec, storage: DatasetStorageManager, *,
            allow_download: bool = True, timeout: float = 60.0,
            max_file_bytes: int | None = None) -> AcquisitionRecord:
    """Acquire the spec's minimal real subset (OPEN + auto-downloadable only)."""
    root = storage.source_root(spec.source)

    # Corpora needing registration / a signed agreement are never auto-downloaded.
    if spec.access_requirement != AccessRequirement.OPEN or not spec.auto_downloadable:
        note = {
            AccessRequirement.REGISTRATION_REQUIRED:
                "requires a signed data-use agreement / account — not auto-downloaded",
            AccessRequirement.RESTRICTED: "restricted access — not auto-downloaded",
            AccessRequirement.OPEN: "open access but not auto-fetched (large or mirror unavailable)",
        }[spec.access_requirement]
        items = tuple(
            AcquisitionItem(relative_path=rel, url=(f"{spec.base_url}/{rel}" if spec.base_url else None),
                            state=AvailabilityState.UNAVAILABLE, note=note)
            for rel in (spec.sample_files or ("<corpus>",)))
        return AcquisitionRecord(source=spec.source, spec_signature=spec_signature(spec),
                                 attempted=False, access_requirement=spec.access_requirement,
                                 items=items, local_root=root, note=note)

    items: list[AcquisitionItem] = []
    for rel in spec.sample_files:
        url = f"{spec.base_url}/{rel}"
        dest = storage.abspath(spec.source, rel)
        # Idempotent: a present, non-empty file is reused (no re-download).
        if os.path.isfile(dest) and os.path.getsize(dest) > 0:
            items.append(AcquisitionItem(
                relative_path=rel, url=url, state=AvailabilityState.DOWNLOADED,
                size_bytes=os.path.getsize(dest), checksum_sha256=sha256_of_file(dest),
                note="already present"))
            continue
        if not allow_download:
            items.append(AcquisitionItem(relative_path=rel, url=url,
                                         state=AvailabilityState.UNAVAILABLE,
                                         note="download disabled (allow_download=False)"))
            continue
        try:
            size = _download(url, dest, timeout=timeout, max_bytes=max_file_bytes)
            items.append(AcquisitionItem(
                relative_path=rel, url=url, state=AvailabilityState.DOWNLOADED,
                size_bytes=size, checksum_sha256=sha256_of_file(dest), note="downloaded"))
        except (urllib.error.URLError, OSError, DownloadError, ValueError) as exc:
            # Clean up any partial artifact; report a structured state (never raise).
            for p in (dest, dest + ".part"):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            items.append(AcquisitionItem(relative_path=rel, url=url,
                                         state=AvailabilityState.UNAVAILABLE,
                                         note=f"download failed: {type(exc).__name__}"))

    return AcquisitionRecord(source=spec.source, spec_signature=spec_signature(spec),
                             attempted=True, access_requirement=spec.access_requirement,
                             items=tuple(items), local_root=root,
                             note="acquired minimal real subset")


def acquire_source(source: DatasetSource, storage: DatasetStorageManager,
                   **kwargs) -> AcquisitionRecord:
    return acquire(spec_for(source), storage, **kwargs)


def plan_all() -> list[AcquisitionRecord]:
    """Acquisition *plan* for every mandatory corpus (no downloads attempted)."""
    storage = DatasetStorageManager()
    return [acquire(spec, storage, allow_download=False) for spec in all_specs()]


__all__ = ["DownloadError", "spec_signature", "acquire", "acquire_source", "plan_all"]
