"""``backend/application_platform/uploads/duplicates.py`` — duplicate-upload detection (DBE-3).

Authoritative, deterministic duplicate detection + classification for the upload workflow.

Root cause (DBE-3, from the Final Hostile QA Audit): re-uploading the same EEG produced the
same content-shape ``upload_id`` but re-registered it with a registry ``content_signature``
that embeds the (advanced) audit head -> ``RegistryError`` -> HTTP 500. The fix is to detect a
duplicate **before** any re-registration and short-circuit deterministically.

Identity model (reuses ``ml.provenance.hash_obj`` — no parallel identity system):

* ``content_hash(bytes)`` — the authoritative content fingerprint of the raw uploaded bytes
  (a true sha-of-content, unlike the existing length-only ``content_fingerprint``). Two
  uploads are *content* duplicates iff their ``content_hash`` matches.
* ``upload_id`` (minted upstream from filename + format + sampling + channels + duration) —
  the *identity* of the recording. Same id + same content -> exact duplicate; same id +
  different content -> conflict; same content + different id -> content duplicate.

This module is pure (no I/O, no registration, never raises) — it only classifies.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import DuplicateClass


def _sha_hex(content: bytes) -> str:
    return hashlib.sha256(bytes(content)).hexdigest()


def content_hash(content: bytes) -> str:
    """Deterministic authoritative content fingerprint of the raw uploaded bytes."""
    return "sha+" + hash_obj({"content_sha": _sha_hex(content)})


@dataclass(frozen=True)
class DuplicateDecision:
    """The classification of an incoming upload against the platform's existing state."""

    classification: DuplicateClass
    content_hash: str
    existing_upload_id: Optional[str] = None
    existing_analysis_id: Optional[str] = None
    detail: str = ""

    @property
    def is_duplicate(self) -> bool:
        return self.classification in (DuplicateClass.EXACT_DUPLICATE,
                                       DuplicateClass.CONTENT_DUPLICATE)

    @property
    def is_conflict(self) -> bool:
        return self.classification == DuplicateClass.CONFLICTING_UPLOAD

    def to_dict(self) -> dict:
        return {"classification": self.classification.value, "content_hash": self.content_hash,
                "existing_upload_id": self.existing_upload_id,
                "existing_analysis_id": self.existing_analysis_id, "detail": self.detail}


class DuplicateDetector:
    """Classifies an incoming upload against an in-memory content/identity index (DBE3-C).

    The index maps:
      * ``content_hash`` -> (upload_id, analysis_id)   — seen content
      * ``upload_id``    -> content_hash               — seen identity

    The detector owns no global state; the caller (the service) holds one detector per
    application instance and records each accepted upload via :meth:`record`.
    """

    def __init__(self) -> None:
        self._by_content: dict[str, tuple] = {}      # content_hash -> (upload_id, analysis_id)
        self._by_upload: dict[str, str] = {}         # upload_id -> content_hash

    def classify(self, *, content: bytes, upload_id: str, valid: bool) -> DuplicateDecision:
        chash = content_hash(content)
        if not valid:
            return DuplicateDecision(DuplicateClass.INVALID_UPLOAD, chash,
                                     detail="upload failed validation")

        seen_content = self._by_content.get(chash)
        seen_upload_content = self._by_upload.get(upload_id)

        if seen_content is not None:
            existing_upload_id, existing_analysis_id = seen_content
            if existing_upload_id == upload_id:
                return DuplicateDecision(
                    DuplicateClass.EXACT_DUPLICATE, chash,
                    existing_upload_id=existing_upload_id,
                    existing_analysis_id=existing_analysis_id,
                    detail="identical content + identity already uploaded")
            return DuplicateDecision(
                DuplicateClass.CONTENT_DUPLICATE, chash,
                existing_upload_id=existing_upload_id,
                existing_analysis_id=existing_analysis_id,
                detail="identical content already uploaded under a different identity")

        if seen_upload_content is not None and seen_upload_content != chash:
            # same identity (filename+shape) but the content hash differs -> real conflict.
            prior = self._by_content.get(seen_upload_content)
            return DuplicateDecision(
                DuplicateClass.CONFLICTING_UPLOAD, chash,
                existing_upload_id=upload_id,
                existing_analysis_id=(prior[1] if prior else None),
                detail="same upload identity already holds different content")

        return DuplicateDecision(DuplicateClass.NEW_UPLOAD, chash, detail="new upload")

    def record(self, *, content_hash_value: str, upload_id: str, analysis_id: str) -> None:
        """Record an accepted, fully-processed upload so later duplicates are detected."""
        self._by_content[content_hash_value] = (upload_id, analysis_id)
        self._by_upload[upload_id] = content_hash_value

    def known_content(self, content_hash_value: str) -> bool:
        return content_hash_value in self._by_content


__all__ = ["content_hash", "DuplicateDecision", "DuplicateDetector"]
