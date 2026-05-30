"""``backend/signal_processing/storage`` — local processed-signal store.

Content-addressed local storage for the cleaned signal (checksum + fingerprint +
integrity verify). Separate from the P1 raw store; the raw EEG is never modified.
No cloud/S3/database/deployment.
"""

from __future__ import annotations

from .store import ProcessedSignalStore

__all__ = ["ProcessedSignalStore"]
