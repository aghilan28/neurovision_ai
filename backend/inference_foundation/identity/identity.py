"""Deterministic prediction-asset identity generation, policy, and validation.

An identity is ``"{kind}+{hash16}"`` (the platform-wide scheme, NR-6). The inference
layer mints only the ``prediction`` kind (a prediction asset), derived from the
``model`` id + the prediction fingerprint — so the same model + same input always
yields the same ``prediction_id`` (idempotent), content-derived, never filename-derived.

It *validates* (but never mints) the ``model``/``training_run``/``dataset``/``feature``/
``signal``/``eeg``/``case``/``patient`` ids it references, so the
Patient -> ... -> Model -> Prediction identity lineage is checkable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import INFERENCE_IDENTITY_VERSION

_ID_RE = re.compile(
    r"^(prediction|model|training_run|dataset|feature|signal|eeg|case|patient)"
    r"\+[0-9a-f]{16}$")


class IdentityError(ValueError):
    """Raised when identity minting or validation fails."""


@dataclass(frozen=True)
class IdentityPolicy:
    kind: str
    required_components: tuple[str, ...]
    parent_kind: Optional[str]
    parent_component: Optional[str]
    mintable: bool = True
    identity_version: str = INFERENCE_IDENTITY_VERSION


IDENTITY_POLICIES: dict[str, IdentityPolicy] = {
    "prediction": IdentityPolicy("prediction", ("model_id", "prediction_key"), "model", "model_id"),
    # Referenced-only kinds (minted upstream); present so this layer can *validate* them.
    "model": IdentityPolicy("model", ("training_run_id", "model_key"), "training_run", "training_run_id", mintable=False),
    "training_run": IdentityPolicy("training_run", ("dataset_id", "training_key"), "dataset", "dataset_id", mintable=False),
    "dataset": IdentityPolicy("dataset", ("source", "dataset_key", "content_key"), None, None, mintable=False),
    "feature": IdentityPolicy("feature", ("processed_id", "feature_key"), "signal", "processed_id", mintable=False),
    "signal": IdentityPolicy("signal", ("eeg_asset_id", "processing_key"), "eeg", "eeg_asset_id", mintable=False),
    "eeg": IdentityPolicy("eeg", ("case_id", "eeg_key"), "case", "case_id", mintable=False),
    "case": IdentityPolicy("case", ("patient_id", "case_key"), "patient", "patient_id", mintable=False),
    "patient": IdentityPolicy("patient", ("patient_key",), None, None, mintable=False),
}


@dataclass(frozen=True)
class Identity:
    id: str
    kind: str
    identity_version: str
    components: dict
    derived_from: Optional[str]

    def to_dict(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "identity_version": self.identity_version,
            "components": self.components, "derived_from": self.derived_from,
        }


def mint_identity(kind: str, components: Mapping[str, object]) -> Identity:
    policy = IDENTITY_POLICIES.get(kind)
    if policy is None:
        raise IdentityError(f"unknown identity kind {kind!r}")
    if not policy.mintable:
        raise IdentityError(f"identity kind {kind!r} is referenced-only and must not be minted here")
    missing = [c for c in policy.required_components
               if c not in components or components[c] in (None, "")]
    if missing:
        raise IdentityError(f"missing required components for {kind!r}: {missing}")

    derived_from = None
    if policy.parent_component is not None:
        derived_from = str(components[policy.parent_component])
        ok, detail = validate_identity(derived_from, expected_kind=policy.parent_kind)
        if not ok:
            raise IdentityError(f"invalid parent identity for {kind!r}: {detail}")

    payload = {
        "kind": kind, "identity_version": policy.identity_version,
        "components": {k: components[k] for k in policy.required_components},
    }
    digest = hash_obj(payload)
    return Identity(id=f"{kind}+{digest}", kind=kind, identity_version=policy.identity_version,
                    components=dict(components), derived_from=derived_from)


def parse_identity(id_str: str) -> tuple[str, str]:
    if not _ID_RE.match(id_str or ""):
        raise IdentityError(f"malformed identity string {id_str!r}")
    kind, digest = id_str.rsplit("+", 1)
    return kind, digest


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.rsplit("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
