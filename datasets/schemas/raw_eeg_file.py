"""Contract: *Raw EEG File*.

The first artifact in the lifecycle. A :class:`RawEegFile` represents a physical
EDF/EDF+ file that has entered the system, identified by the SHA-256 of its bytes
(content-addressed). It carries *no* interpreted metadata yet — only what can be
known from the file as bytes plus its detected container format.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datasets.schemas.enums import FileFormat


@dataclass(frozen=True, slots=True)
class RawEegFile:
    """A raw EEG file on entry, before validation/metadata extraction.

    ``file_id`` and ``content_sha256`` are deterministic functions of the file
    bytes, which is what makes duplicate detection exact and content-addressed.
    ``source_path`` is provenance (where it came from) and is intentionally *not*
    part of the content identity — the same bytes from two paths are one file.
    """

    file_id: str
    content_sha256: str
    file_name: str
    file_size_bytes: int
    detected_format: FileFormat
    source_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "content_sha256": self.content_sha256,
            "file_name": self.file_name,
            "file_size_bytes": self.file_size_bytes,
            "detected_format": self.detected_format.value,
            "source_path": self.source_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawEegFile:
        return cls(
            file_id=data["file_id"],
            content_sha256=data["content_sha256"],
            file_name=data["file_name"],
            file_size_bytes=int(data["file_size_bytes"]),
            detected_format=FileFormat(data["detected_format"]),
            source_path=data.get("source_path"),
        )
