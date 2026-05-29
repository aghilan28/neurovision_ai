"""Deterministic, checksummed artifact storage.

Why not ``np.savez``? Zip archives embed file timestamps, so the bytes are not
reproducible and a checksum would change run-to-run. Instead, weights are written
with a custom *deterministic* container:

    [8-byte big-endian header length][canonical-JSON index][concatenated raw bytes]

The index maps each array name (sorted) to its dtype, shape and byte range. The
result is byte-identical for identical weights, so its sha256 is a stable artifact
checksum (AP-6 / NR-10). JSON artifacts use canonical (sorted, compact) encoding
for the same reason.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from ..version import ARTIFACT_VERSION
from ..provenance import canonical_json, full_sha256, write_json, read_json


# --- deterministic weights (de)serialization ----------------------------------
_MAGIC = b"NVAI-W1\x00"


def serialize_weights(weights: Mapping[str, np.ndarray]) -> bytes:
    """Serialize a flat ``{name: ndarray}`` mapping to deterministic bytes."""
    index: dict[str, dict] = {}
    chunks: list[bytes] = []
    offset = 0
    for name in sorted(weights):
        arr = np.ascontiguousarray(weights[name])
        raw = arr.tobytes()
        index[name] = {
            "dtype": str(arr.dtype),
            "shape": list(arr.shape),
            "offset": offset,
            "nbytes": len(raw),
        }
        chunks.append(raw)
        offset += len(raw)
    header = canonical_json({"artifact_version": ARTIFACT_VERSION, "index": index}).encode("utf-8")
    return _MAGIC + len(header).to_bytes(8, "big") + header + b"".join(chunks)


def deserialize_weights(blob: bytes) -> dict[str, np.ndarray]:
    """Inverse of :func:`serialize_weights`."""
    if blob[: len(_MAGIC)] != _MAGIC:
        raise ValueError("not a NeuroVision weights blob")
    pos = len(_MAGIC)
    header_len = int.from_bytes(blob[pos : pos + 8], "big")
    pos += 8
    header = canonical_load(blob[pos : pos + header_len])
    pos += header_len
    data = blob[pos:]
    out: dict[str, np.ndarray] = {}
    for name, meta in header["index"].items():
        start = meta["offset"]
        raw = data[start : start + meta["nbytes"]]
        arr = np.frombuffer(raw, dtype=np.dtype(meta["dtype"])).reshape(meta["shape"])
        out[name] = arr.copy()  # own the memory (frombuffer is read-only)
    return out


def canonical_load(data: bytes) -> Any:
    import json

    return json.loads(data.decode("utf-8"))


# --- artifact references + store ----------------------------------------------
@dataclass(frozen=True)
class ArtifactRef:
    """A content-addressed reference to a stored artifact."""

    name: str
    kind: str           # "weights" | "json"
    relpath: str
    checksum: str       # full sha256 of the on-disk bytes
    size_bytes: int
    artifact_version: str = ARTIFACT_VERSION

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "relpath": self.relpath,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "artifact_version": self.artifact_version,
        }


class ArtifactStore:
    """A filesystem-backed artifact store with checksums and a manifest.

    All paths are relative to ``root``. The manifest (``_manifest.json``) lists
    every registered artifact and its checksum, enabling integrity verification
    and detection of silent edits.
    """

    MANIFEST_NAME = "_manifest.json"

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)
        self._refs: dict[str, ArtifactRef] = {}

    # --- low-level ------------------------------------------------------------
    def _abspath(self, relpath: str) -> str:
        return os.path.join(self.root, relpath)

    def save_weights(self, name: str, weights: Mapping[str, np.ndarray]) -> ArtifactRef:
        relpath = f"{name}.weights.bin"
        blob = serialize_weights(weights)
        path = self._abspath(relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(blob)
        ref = ArtifactRef(
            name=name, kind="weights", relpath=relpath,
            checksum=full_sha256(blob), size_bytes=len(blob),
        )
        self._register(ref)
        return ref

    def load_weights(self, ref: ArtifactRef) -> dict[str, np.ndarray]:
        with open(self._abspath(ref.relpath), "rb") as fh:
            blob = fh.read()
        if full_sha256(blob) != ref.checksum:
            raise IntegrityError(f"checksum mismatch for {ref.name} (silent modification?)")
        return deserialize_weights(blob)

    def save_json(self, name: str, obj: Any) -> ArtifactRef:
        relpath = f"{name}.json"
        path = self._abspath(relpath)
        checksum = write_json(path, obj)
        size = os.path.getsize(path)
        ref = ArtifactRef(name=name, kind="json", relpath=relpath, checksum=checksum, size_bytes=size)
        self._register(ref)
        return ref

    def load_json(self, ref: ArtifactRef) -> Any:
        from ..provenance import sha256_of_file

        if sha256_of_file(self._abspath(ref.relpath)) != ref.checksum:
            raise IntegrityError(f"checksum mismatch for {ref.name} (silent modification?)")
        return read_json(self._abspath(ref.relpath))

    # --- manifest / integrity -------------------------------------------------
    def _register(self, ref: ArtifactRef) -> None:
        self._refs[ref.name] = ref
        self._write_manifest()

    def _write_manifest(self) -> None:
        manifest = {
            "artifact_version": ARTIFACT_VERSION,
            "artifacts": {name: r.to_dict() for name, r in sorted(self._refs.items())},
        }
        write_json(self._abspath(self.MANIFEST_NAME), manifest)

    def verify(self, ref: ArtifactRef | None = None) -> bool:
        """Verify one artifact (or all) against its recorded checksum."""
        from ..provenance import sha256_of_file

        refs = [ref] if ref is not None else list(self._refs.values())
        for r in refs:
            path = self._abspath(r.relpath)
            if not os.path.exists(path):
                return False
            if sha256_of_file(path) != r.checksum:
                return False
        return True

    def manifest(self) -> dict:
        return {
            "root": self.root,
            "artifact_version": ARTIFACT_VERSION,
            "artifacts": {name: r.to_dict() for name, r in sorted(self._refs.items())},
        }


class IntegrityError(RuntimeError):
    """Raised when an artifact's bytes do not match its recorded checksum."""
