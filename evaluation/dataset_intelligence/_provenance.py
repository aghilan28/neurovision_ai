"""Shared provenance helpers for dataset-intelligence analyzers.

The *input fingerprint* of an analysis is a deterministic, order-independent
content fingerprint of the record set (by ``content_sha256`` + ``file_id``). It
ties every report to the exact inputs that produced it, so reports are traceable
and reproducible (AP-5/AP-6, NR-10/NR-11).
"""

from __future__ import annotations

from collections.abc import Sequence

from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation._canonical import canonical_fingerprint
from evaluation.dataset_intelligence._version import DATASET_INTELLIGENCE_VERSION
from evaluation.dataset_intelligence.schemas.common import Provenance


def records_fingerprint(records: Sequence[ValidatedEegRecord]) -> str:
    """Deterministic, order-independent fingerprint of a record set's content."""
    members = sorted(
        (r.raw_file.content_sha256, r.file_id) for r in records
    )
    return canonical_fingerprint({"records": members})


def build_provenance(
    records: Sequence[ValidatedEegRecord],
    *,
    dataset_id: str | None = None,
    dataset_version: str | None = None,
    generated_at: str | None = None,
) -> Provenance:
    """Build the :class:`Provenance` block stamped on a report."""
    return Provenance(
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        intelligence_version=DATASET_INTELLIGENCE_VERSION,
        input_fingerprint=records_fingerprint(records),
        n_records=len(records),
        generated_at=generated_at,
    )
