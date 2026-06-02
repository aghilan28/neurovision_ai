"""EEG lineage helpers built on ml.lineage.

Every EEG asset gets a content-addressed lineage node whose parent is the **Case**
lineage node it is ingested under. Because the case node parents the patient node,
``verify_chain`` from an EEG asset spans the required chain **Patient → Case → EEG
Asset**. Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel
lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    EEG_FOUNDATION_VERSION, EEG_DOMAIN_VERSION, EEG_IDENTITY_VERSION, EEG_LINEAGE_VERSION,
    DETERMINISTIC_EPOCH,
)


def eeg_version_bundle(**extra: object) -> dict:
    bundle = {
        "eeg_foundation_version": EEG_FOUNDATION_VERSION,
        "eeg_domain_version": EEG_DOMAIN_VERSION,
        "eeg_identity_version": EEG_IDENTITY_VERSION,
        "eeg_lineage_version": EEG_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_eeg_lineage(eeg_id: str, *, fmt: str, parents: Sequence[str] = (),
                     case_id: str | None = None, reason: str = "ingested",
                     created_at: str = DETERMINISTIC_EPOCH,
                     extra: dict | None = None) -> LineageRecord:
    """An EEG-asset lineage node parented by the Case node (Patient → Case → EEG Asset)."""
    outputs = {"eeg_id": eeg_id, "reason": reason}
    if extra:
        outputs.update(extra)
    return make_lineage_record(
        kind="eeg_asset", versions=eeg_version_bundle(eeg_format=fmt),
        inputs={"eeg_id": eeg_id, "format": fmt, "case_id": case_id},
        outputs=outputs, parents=tuple(p for p in parents if p), created_at=created_at)


__all__ = ["eeg_version_bundle", "make_eeg_lineage"]
