"""Signal lineage helpers built on the shared ``ml.lineage`` machinery.

No parallel lineage system: a processed-EEG node is recorded in the *same*
``ml.lineage.LineageTracker`` as the Patient/Case/EEG nodes, parenting the raw EEG
asset's node. A single ``verify_chain`` from a processed asset therefore reaches:

    Patient -> Case -> EEG Asset -> Processed EEG

connecting the cleaned signal back to the patient with complete traceability.
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    SIGNAL_PROCESSING_VERSION, SIGNAL_DOMAIN_VERSION, SIGNAL_IDENTITY_VERSION,
    SIGNAL_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def signal_version_bundle(**extra: object) -> dict:
    """The signal-processing version coordinates embedded in every signal lineage node."""
    bundle = {
        "signal_processing_version": SIGNAL_PROCESSING_VERSION,
        "signal_domain_version": SIGNAL_DOMAIN_VERSION,
        "signal_identity_version": SIGNAL_IDENTITY_VERSION,
        "signal_lineage_version": SIGNAL_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_signal_lineage(processed_id: str, eeg_asset_id: str, eeg_lineage_id: str, *,
                        quality_id: str, processing_id: str, processed_fingerprint: str,
                        created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A content-addressed processed-EEG lineage node, parented on the raw EEG node."""
    return make_lineage_record(
        kind="processed_eeg",
        versions=signal_version_bundle(),
        inputs={"eeg_asset_id": eeg_asset_id, "quality_id": quality_id,
                "processing_id": processing_id},
        outputs={"processed_id": processed_id, "processed_fingerprint": processed_fingerprint},
        parents=(eeg_lineage_id,),
        created_at=created_at,
    )
