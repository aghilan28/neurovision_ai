"""``ml/artifacts`` — versioned, checksummed artifact tracking (V1-P5).

Every artifact the ML layer writes — model weights, configs, training reports,
metrics, benchmark records, lineage records — is content-addressed with a sha256
checksum and registered in a manifest. This makes silent modification detectable
(``verify``) and gives the registry/lineage stable references (AP-5 / AP-8 / NR-11).
"""

from __future__ import annotations

from .store import (
    ArtifactRef,
    ArtifactStore,
    serialize_weights,
    deserialize_weights,
)

__all__ = ["ArtifactRef", "ArtifactStore", "serialize_weights", "deserialize_weights"]
