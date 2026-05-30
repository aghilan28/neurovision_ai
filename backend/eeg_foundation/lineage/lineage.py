"""EEG lineage helpers built on the shared ``ml.lineage`` machinery.

No parallel lineage system: EEG nodes are recorded in the *same*
``ml.lineage.LineageTracker`` as the clinical Case/Patient nodes, with the EEG node
parenting the case lineage node. A single ``verify_chain`` from an EEG asset
therefore reaches:

    Patient -> Case -> EEG Asset

connecting the real EEG recording to the patient with complete traceability.
"""

from __future__ import annotations


from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    EEG_FOUNDATION_VERSION,
    EEG_DOMAIN_VERSION,
    EEG_IDENTITY_VERSION,
    EEG_LINEAGE_VERSION,
    DETERMINISTIC_EPOCH,
)


def eeg_version_bundle(**extra: object) -> dict:
    """The EEG version coordinates embedded in every EEG lineage node."""
    bundle = {
        "eeg_foundation_version": EEG_FOUNDATION_VERSION,
        "eeg_domain_version": EEG_DOMAIN_VERSION,
        "eeg_identity_version": EEG_IDENTITY_VERSION,
        "eeg_lineage_version": EEG_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_eeg_lineage(asset_id: str, case_id: str, case_lineage_id: str, *,
                     recording_id: str, eeg_format: str, checksum_sha256: str,
                     created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A content-addressed EEG lineage node, parented on the case lineage node."""
    return make_lineage_record(
        kind="eeg",
        versions=eeg_version_bundle(),
        inputs={"case_id": case_id, "asset_id": asset_id, "recording_id": recording_id},
        outputs={"asset_id": asset_id, "eeg_format": eeg_format, "checksum_sha256": checksum_sha256},
        parents=(case_lineage_id,),
        created_at=created_at,
    )
