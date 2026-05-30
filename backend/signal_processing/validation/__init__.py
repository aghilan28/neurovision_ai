"""``backend/signal_processing/validation`` — processed-asset integrity validation.

``SignalIntegrityValidator`` checks identity/registry/storage/quality/processing-
traceability/artifacts/audit/lineage/version consistency plus the cardinal P2
invariants (raw EEG immutability, raw -> processed traceability), reusing
``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from .integrity import SignalIntegrityValidator

__all__ = ["SignalIntegrityValidator"]
