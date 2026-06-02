"""``datasets.ingestion`` — deterministic EDF/EDF+ ingestion.

This subpackage turns a physical EDF/EDF+ file into in-memory, structured data:

* :mod:`datasets.ingestion.edf_reader` — a pure-Python EDF/EDF+ reader (header,
  per-channel signals, EDF+ annotations). No third-party EDF dependency, for full
  determinism and traceability.
* :mod:`datasets.ingestion.signature` — file-signature / format detection.
* :mod:`datasets.ingestion.integrity` — binary integrity verification.
* :mod:`datasets.ingestion.discovery` — channel / sampling-rate / duration discovery.
* :mod:`datasets.ingestion.pipeline` — the deterministic ingestion pipeline that
  produces a :class:`~datasets.schemas.validated_record.ValidatedEegRecord`.

**Supported inputs (V1): EDF and EDF+ only.** Other formats are detected and
reported as ``UNSUPPORTED`` rather than parsed (V1 directive; Rule NR-13). Future
format support is documented as an extension point in ``datasets/docs``.
"""

from __future__ import annotations

from datasets.ingestion.discovery import (
    discover_channels,
    discover_duration_seconds,
    discover_sampling_rates,
)
from datasets.ingestion.edf_reader import (
    EdfFileHeader,
    EdfReadError,
    EdfReading,
    EdfSignalHeader,
    read_edf,
    read_edf_header,
)
from datasets.ingestion.integrity import verify_integrity
from datasets.ingestion.pipeline import IngestionError, ingest_edf_file
from datasets.ingestion.signature import detect_format, sniff_signature

__all__ = [
    "EdfFileHeader",
    "EdfReadError",
    "EdfReading",
    "EdfSignalHeader",
    "IngestionError",
    "detect_format",
    "discover_channels",
    "discover_duration_seconds",
    "discover_sampling_rates",
    "ingest_edf_file",
    "read_edf",
    "read_edf_header",
    "sniff_signature",
    "verify_integrity",
]
