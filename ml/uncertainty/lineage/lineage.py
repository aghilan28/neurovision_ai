"""Build uncertainty lineage records on top of ml.lineage."""

from __future__ import annotations

from typing import Mapping

from ...lineage import VersionBundle, make_lineage_record, LineageRecord
from ...version import DETERMINISTIC_EPOCH


def make_uncertainty_lineage(
    *,
    version_bundle: VersionBundle,
    inputs: Mapping[str, object],
    outputs: Mapping[str, object],
    parents: tuple[str, ...],
    created_at: str = DETERMINISTIC_EPOCH,
) -> LineageRecord:
    """Create a content-addressed 'uncertainty' lineage record.

    ``parents`` should include the model-training lineage id and the evaluation
    lineage id so the uncertainty output is traceable to the model and the
    patient-disjoint evaluation it was calibrated/validated against.
    """
    return make_lineage_record(
        kind="uncertainty",
        versions=version_bundle,
        inputs=inputs,
        outputs=outputs,
        parents=parents,
        created_at=created_at,
    )
