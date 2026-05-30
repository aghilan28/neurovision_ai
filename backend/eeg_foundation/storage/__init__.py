"""``backend/eeg_foundation/storage`` — local EEG storage abstraction (P1-E).

A content-addressed local filesystem store for raw EEG bytes with checksum +
fingerprint integrity. No cloud/S3/database/deployment — only correct architecture
behind the ``EEGStorageRecord`` contract.
"""

from __future__ import annotations

from .store import LocalEEGStore, fingerprint_of_checksum

__all__ = ["LocalEEGStore", "fingerprint_of_checksum"]
