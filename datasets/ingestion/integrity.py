"""Binary integrity verification for EDF/EDF+ files.

Integrity here means: *does the file's byte length agree with what its header
declares?* An EDF file's data section must be exactly
``num_data_records * record_size_bytes`` long. A mismatch indicates truncation or
corruption, which we report as structured evidence (an
:class:`~datasets.schemas.reports.IntegrityResult`) rather than failing silently.
"""

from __future__ import annotations

import os

from datasets.ingestion.edf_reader import (
    MAIN_HEADER_BYTES,
    SIGNAL_HEADER_BYTES,
    EdfFileHeader,
)
from datasets.schemas.reports import IntegrityResult


def verify_integrity(path: str, header: EdfFileHeader) -> IntegrityResult:
    """Verify that ``path``'s size is consistent with its decoded ``header``.

    The result is deterministic and records both the declared and computed record
    counts so a reviewer can see *how* the conclusion was reached (auditability).
    """
    actual_size = os.path.getsize(path)
    header_len = MAIN_HEADER_BYTES + header.num_signals * SIGNAL_HEADER_BYTES
    record_bytes = header.record_size_bytes
    data_len = max(actual_size - header_len, 0)

    notes: list[str] = []

    if record_bytes == 0:
        computed_records = 0
        notes.append("record_size_bytes is zero (no samples per record)")
    else:
        computed_records = data_len // record_bytes

    declared = header.num_data_records
    if declared < 0:
        # EDF allows an unknown record count (-1); the computed count is authoritative.
        expected_size = header_len + computed_records * record_bytes
        ok = actual_size >= header_len
        notes.append("num_data_records was -1 (unknown); used computed count")
    else:
        expected_size = header_len + declared * record_bytes
        ok = actual_size == expected_size
        if record_bytes and data_len % record_bytes != 0:
            notes.append("data section is not an exact multiple of the record size")
        if computed_records < declared:
            notes.append(
                f"file holds {computed_records} full records but header declares {declared}"
            )

    return IntegrityResult(
        ok=ok,
        expected_size_bytes=expected_size,
        actual_size_bytes=actual_size,
        declared_data_records=declared,
        computed_data_records=computed_records,
        record_size_bytes=record_bytes,
        notes=tuple(notes),
    )
