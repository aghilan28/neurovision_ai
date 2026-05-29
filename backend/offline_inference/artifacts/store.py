"""Inference artifact store (wraps the deterministic ml artifact store).

Backend may import ml (NR-8). Rather than re-implement checksummed storage, this
composes ``ml.artifacts.ArtifactStore`` and adds inference-specific helpers for
persisting typed output contracts and reports under a stable, namespaced layout.
"""

from __future__ import annotations

from typing import Any

import json
import os

from ml.artifacts import ArtifactStore, ArtifactRef  # allowed: backend -> ml
from ml.provenance import sha256_of_file

from ..version import INFERENCE_ARTIFACT_VERSION


def verify_directory(root: str) -> tuple[bool, dict]:
    """Re-verify a persisted run directory against its on-disk manifest.

    Reads ``_manifest.json`` and recomputes the sha256 of every listed artifact,
    detecting any silent modification after the run (used by the ArtifactJob and
    the application's artifact-consistency validation).
    """
    manifest_path = os.path.join(root, ArtifactStore.MANIFEST_NAME)
    if not os.path.exists(manifest_path):
        return False, {"error": "manifest missing", "root": root}
    with open(manifest_path, "rb") as fh:
        manifest = json.loads(fh.read().decode("utf-8"))
    details: dict = {"n_checked": 0, "n_ok": 0, "mismatched": [], "missing": []}
    for name, ref in manifest.get("artifacts", {}).items():
        path = os.path.join(root, ref["relpath"])
        details["n_checked"] += 1
        if not os.path.exists(path):
            details["missing"].append(name)
            continue
        if sha256_of_file(path) == ref["checksum"]:
            details["n_ok"] += 1
        else:
            details["mismatched"].append(name)
    ok = not details["mismatched"] and not details["missing"]
    return ok, details


class InferenceArtifactStore:
    """A checksummed artifact store for offline-inference outputs."""

    def __init__(self, root: str):
        self._store = ArtifactStore(root)

    @property
    def root(self) -> str:
        return self._store.root

    def save_output(self, name: str, output_contract: Any) -> ArtifactRef:
        """Persist a typed output contract (anything with ``to_dict``)."""
        return self._store.save_json(name, output_contract.to_dict())

    def save_json(self, name: str, obj: Any) -> ArtifactRef:
        return self._store.save_json(name, obj)

    def load_json(self, ref: ArtifactRef) -> Any:
        return self._store.load_json(ref)

    def verify(self, ref: ArtifactRef | None = None) -> bool:
        return self._store.verify(ref)

    def manifest(self) -> dict:
        m = self._store.manifest()
        m["inference_artifact_version"] = INFERENCE_ARTIFACT_VERSION
        return m

    def refs(self) -> dict:
        """name -> artifact ref dict (for building the ArtifactOutput contract)."""
        return {name: r.to_dict() for name, r in self._store._refs.items()}
