"""Deterministic clinical-validation identity generation and validation.

An identity is ``"{kind}+{hash16}"`` (the platform-wide scheme, NR-6). This layer mints the
validation kinds — ``validation_benchmark``, ``validation_performance``,
``validation_reliability``, ``validation_calibration``, ``validation_comparison``,
``validation_evidence``, ``validation_readiness``, ``clinical_validation`` — each
content-addressed from its inputs (identical inputs reproduce identical ids). The upstream
``model``/``dataset`` ids are minted by their owning subsystems and only *validated* here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import CLINICAL_IDENTITY_VERSION

_KINDS = (
    "validation_benchmark", "validation_performance", "validation_reliability",
    "validation_calibration", "validation_comparison", "validation_evidence",
    "validation_readiness", "clinical_validation",
)
_ID_RE = re.compile(r"^(" + "|".join(_KINDS) + r"|model|dataset|production_model)\+[0-9a-f]{16}$")

_REQUIRED = {
    "validation_benchmark": ("model_id", "metrics_key"),
    "validation_performance": ("model_id", "perf_key"),
    "validation_reliability": ("model_id", "reliability_key"),
    "validation_calibration": ("model_id", "calibration_key"),
    "validation_comparison": ("comparison_key",),
    "validation_evidence": ("model_id", "evidence_key"),
    "validation_readiness": ("target_id", "readiness_key"),
    "clinical_validation": ("model_id", "evidence_id"),
}


class IdentityError(ValueError):
    """Raised when identity minting or validation fails."""


@dataclass(frozen=True)
class Identity:
    id: str
    kind: str
    identity_version: str
    components: dict

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "identity_version": self.identity_version,
                "components": self.components}


def mint_identity(kind: str, components: Mapping[str, object]) -> Identity:
    if kind not in _REQUIRED:
        raise IdentityError(f"unknown identity kind {kind!r}")
    missing = [c for c in _REQUIRED[kind] if c not in components or components[c] in (None, "")]
    if missing:
        raise IdentityError(f"missing required components for {kind!r}: {missing}")
    payload = {"kind": kind, "identity_version": CLINICAL_IDENTITY_VERSION,
               "components": {k: components[k] for k in _REQUIRED[kind]}}
    return Identity(id=f"{kind}+{hash_obj(payload)}", kind=kind,
                    identity_version=CLINICAL_IDENTITY_VERSION, components=dict(components))


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.rsplit("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
