"""Version identities for the EEG Foundation Layer (Productization P1).

Every EEG-foundation artifact records the versions that produced it, so it is
reproducible and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

The EEG Foundation is the platform's first **real-EEG** capability: a real EEG file
enters, is loaded, validated, parsed, normalized into metadata, fingerprinted, stored
(by reference), registered, lineage-tracked, and audited. Nothing more — no signal
filtering, artifact removal, feature extraction, inference, or analytics (those are
later productization phases and are explicitly out of scope here).

Format readers are **spec-compliant pure-Python + NumPy** implementations that read
the real bytes of real files. This preserves the platform's non-negotiable
framework-free, pinned, bit-for-bit reproducible runtime (NR-10 / AP-6): no new
third-party dependency is introduced.
"""

from __future__ import annotations

EEG_FOUNDATION_VERSION: str = "eeg-foundation@1.0.0"

EEG_DOMAIN_VERSION: str = "eeg-domain@1.0.0"
EEG_IDENTITY_VERSION: str = "eeg-identity@1.0.0"
EEG_INGESTION_VERSION: str = "eeg-ingestion@1.0.0"
EEG_FORMAT_VERSION: str = "eeg-format@1.0.0"
EEG_METADATA_VERSION: str = "eeg-metadata@1.0.0"
EEG_VALIDATION_VERSION: str = "eeg-validation@1.0.0"
EEG_STORAGE_VERSION: str = "eeg-storage@1.0.0"
EEG_REGISTRY_VERSION: str = "eeg-registry@1.0.0"
EEG_AUDIT_VERSION: str = "eeg-audit@1.0.0"
EEG_LINEAGE_VERSION: str = "eeg-lineage@1.0.0"
EEG_REPORT_VERSION: str = "eeg-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
