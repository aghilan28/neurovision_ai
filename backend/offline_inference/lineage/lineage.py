"""Build inference lineage records on top of ml.lineage."""

from __future__ import annotations

from typing import Mapping

from ml.lineage import VersionBundle, make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import DETERMINISTIC_EPOCH


def make_inference_lineage(
    *,
    version_bundle: VersionBundle,
    inputs: Mapping[str, object],
    outputs: Mapping[str, object],
    parents: tuple[str, ...] = (),
    created_at: str = DETERMINISTIC_EPOCH,
) -> LineageRecord:
    """Create a content-addressed 'inference' lineage record.

    ``parents`` should include the model-training, evaluation, and uncertainty
    lineage ids so the inference output is traceable to everything that produced it.
    """
    return make_lineage_record(
        kind="inference",
        versions=version_bundle,
        inputs=inputs,
        outputs=outputs,
        parents=parents,
        created_at=created_at,
    )
