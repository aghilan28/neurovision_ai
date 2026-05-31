"""``backend/dataset_acquisition/connectors`` — Real Dataset Connectors (T1-C).

Connect to a dataset **on disk** and extract everything from the **actual files** (never
manifests): discovery, recording enumeration, channel / sampling / duration / patient /
session extraction, and label enumeration. Recording reading reuses the platform's real
``eeg_foundation`` MNE reader (no parallel parser); recording ids reuse the
``eeg_foundation`` content-addressed ``recording+{hash16}`` id.

``ChbMitConnector`` additionally parses ``chbNN-summary.txt`` for real per-recording seizure
labels (start/end seconds), so CHB-MIT no longer needs synthetic labels. A generic
``EdfDirectoryConnector`` handles any EDF tree without labels.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from backend.eeg_foundation.ingestion.reader import load_eeg  # sibling backend (allowed)
from backend.eeg_foundation.metadata.extractor import compute_recording_id

from ..identity import mint_identity
from ..models.domain import (
    DatasetSource, LabelRecord, LabelScheme, LabelValue, PatientRecord, RecordingFormat,
    RecordingRecord, SeizureInterval,
)
from ..storage import DatasetStorageManager

# eeg_foundation EEGFormat.value -> Track-1 RecordingFormat
_FORMAT_MAP = {
    "EDF": RecordingFormat.EDF, "EDF+": RecordingFormat.EDF_PLUS,
    "BDF": RecordingFormat.BDF, "BDF+": RecordingFormat.BDF_PLUS,
    "FIF": RecordingFormat.FIF, "SET": RecordingFormat.SET,
}

_SEIZURE_COUNT_RE = re.compile(r"Number of Seizures in File:\s*(\d+)", re.IGNORECASE)
_SEIZURE_START_RE = re.compile(r"Seizure(?:\s+\d+)?\s+Start Time:\s*(\d+)\s*seconds", re.IGNORECASE)
_SEIZURE_END_RE = re.compile(r"Seizure(?:\s+\d+)?\s+End Time:\s*(\d+)\s*seconds", re.IGNORECASE)
_FILE_NAME_RE = re.compile(r"File Name:\s*(\S+)", re.IGNORECASE)


@dataclass(frozen=True)
class ConnectorResult:
    source: DatasetSource
    label_scheme: LabelScheme
    discovered_files: tuple
    recordings: tuple                     # (RecordingRecord, ...)
    patients: tuple                       # (PatientRecord, ...)
    labels: tuple                         # (LabelRecord, ...)
    summary_files: tuple = ()

    def to_dict(self) -> dict:
        return {"source": self.source.value, "label_scheme": self.label_scheme.value,
                "n_discovered": len(self.discovered_files),
                "n_recordings": len(self.recordings), "n_patients": len(self.patients),
                "n_labels": len(self.labels),
                "discovered_files": list(self.discovered_files),
                "recordings": [r.to_dict() for r in self.recordings],
                "patients": [p.to_dict() for p in self.patients],
                "labels": [label.to_dict() for label in self.labels],
                "summary_files": list(self.summary_files)}


def parse_chb_summary(text: str) -> dict:
    """Parse a ``chbNN-summary.txt`` into ``{edf_filename: (n_seizures, [(start,end), ...])}``.

    Handles both the early format (``Seizure Start Time:``) and the later per-index format
    (``Seizure 1 Start Time:``). Real CHB-MIT annotations — the basis of real labels.
    """
    out: dict[str, tuple] = {}
    current: str | None = None
    n_seizures = 0
    starts: list[int] = []
    ends: list[int] = []

    def _flush():
        if current is not None:
            intervals = [(float(s), float(e)) for s, e in zip(starts, ends)]
            out[current] = (n_seizures, intervals)

    for raw in text.splitlines():
        line = raw.strip()
        m = _FILE_NAME_RE.match(line)
        if m:
            _flush()
            current = os.path.basename(m.group(1))
            n_seizures, starts, ends = 0, [], []
            continue
        m = _SEIZURE_COUNT_RE.search(line)
        if m:
            n_seizures = int(m.group(1))
            continue
        m = _SEIZURE_START_RE.search(line)
        if m:
            starts.append(int(m.group(1)))
            continue
        m = _SEIZURE_END_RE.search(line)
        if m:
            ends.append(int(m.group(1)))
            continue
    _flush()
    return out


class RealDatasetConnector:
    """Base connector: discovers + reads real recordings from disk (no labels)."""

    source: DatasetSource = DatasetSource.OTHER
    label_scheme: LabelScheme = LabelScheme.NONE
    recording_suffixes: tuple = (".edf", ".bdf", ".fif", ".set")

    def __init__(self, storage: DatasetStorageManager) -> None:
        self.storage = storage

    # --- overridable structure rules -----------------------------------------
    def patient_key_for(self, relative_path: str) -> str:
        stem = os.path.splitext(os.path.basename(relative_path))[0]
        return stem.split("_")[0] if "_" in stem else (relative_path.split("/")[0] or stem)

    def session_key_for(self, relative_path: str) -> str:
        return self.patient_key_for(relative_path)

    def discover(self) -> list:
        return self.storage.list_files(self.source, suffixes=self.recording_suffixes)

    # --- recording reading (ACTUAL files via the eeg_foundation reader) -------
    def _read_recording(self, relative_path: str) -> RecordingRecord:
        abspath = self.storage.abspath(self.source, relative_path)
        parsed = load_eeg(abspath)
        fmt = (_FORMAT_MAP.get(parsed.detected_format.value, RecordingFormat.OTHER)
               if parsed.detected_format else RecordingFormat.OTHER)
        recording_id = (compute_recording_id(parsed) if parsed.parse_ok
                        else "recording+" + (parsed.checksum_sha256[:16] or "0" * 16))
        return RecordingRecord(
            recording_id=recording_id,
            patient_id=self.patient_key_for(relative_path),
            session_id=self.session_key_for(relative_path),
            relative_path=relative_path, fmt=fmt, parse_ok=parsed.parse_ok,
            sampling_frequency=parsed.sampling_frequency, duration_seconds=parsed.duration_seconds,
            n_samples=parsed.n_samples, n_channels=parsed.n_channels,
            channel_labels=tuple(c.label for c in parsed.channels),
            n_annotations=len(parsed.annotations), checksum_sha256=parsed.checksum_sha256,
            file_size_bytes=parsed.file_size_bytes, error=parsed.error)

    def extract_labels(self, recordings: list) -> list:
        """Default: no label scheme (overridden by labelled connectors)."""
        return []

    def connect(self) -> ConnectorResult:
        discovered = self.discover()
        recordings = [self._read_recording(rel) for rel in discovered]
        labels = self.extract_labels(recordings)
        label_by_recording = {label.recording_id: label.label_id for label in labels}
        recordings = [
            (r if r.recording_id not in label_by_recording
             else _with_label(r, label_by_recording[r.recording_id]))
            for r in recordings
        ]
        patients = self._build_patients(recordings)
        return ConnectorResult(
            source=self.source, label_scheme=self.label_scheme,
            discovered_files=tuple(discovered), recordings=tuple(recordings),
            patients=tuple(patients), labels=tuple(labels),
            summary_files=tuple(getattr(self, "_summary_files", ())))

    def _build_patients(self, recordings: list) -> list:
        by_patient: dict[str, list] = {}
        for r in recordings:
            by_patient.setdefault(r.patient_id, []).append(r)
        patients = []
        for key in sorted(by_patient):
            recs = by_patient[key]
            sessions = sorted({r.session_id for r in recs})
            pid = mint_identity("dataset_patient",
                                {"source": self.source.value, "patient_key": key}).id
            patients.append(PatientRecord(
                patient_id=pid, patient_key=key, source=self.source,
                n_recordings=len(recs), n_sessions=len(sessions),
                recording_ids=tuple(sorted(r.recording_id for r in recs))))
        # rewrite recordings' patient_id from key -> minted id is done by the service;
        # here patient_id stays the key for grouping. (service maps via patient_key)
        return patients


def _with_label(rec: RecordingRecord, label_id: str) -> RecordingRecord:
    from dataclasses import replace
    return replace(rec, label_id=label_id)


class EdfDirectoryConnector(RealDatasetConnector):
    """Generic connector for an EDF/BDF/FIF/SET tree with no label scheme."""

    def __init__(self, storage: DatasetStorageManager, source: DatasetSource) -> None:
        super().__init__(storage)
        self.source = source
        self.label_scheme = LabelScheme.NONE


class ChbMitConnector(RealDatasetConnector):
    """CHB-MIT connector: reads real EDF recordings + parses real seizure summaries."""

    source = DatasetSource.CHB_MIT
    label_scheme = LabelScheme.CHB_MIT_SEIZURE
    recording_suffixes = (".edf",)

    def __init__(self, storage: DatasetStorageManager) -> None:
        super().__init__(storage)
        self._summary_files: tuple = ()

    def _summary_map(self) -> dict:
        """Aggregate every ``*-summary.txt`` under the source root (real annotations)."""
        summaries = self.storage.list_files(self.source, suffixes=("-summary.txt",))
        self._summary_files = tuple(summaries)
        merged: dict[str, tuple] = {}
        for rel in summaries:
            with open(self.storage.abspath(self.source, rel), encoding="utf-8",
                      errors="replace") as fh:
                merged.update(parse_chb_summary(fh.read()))
        return merged

    def extract_labels(self, recordings: list) -> list:
        summary = self._summary_map()
        labels: list = []
        for rec in recordings:
            fname = os.path.basename(rec.relative_path)
            if fname not in summary:
                continue  # no annotation for this recording -> missing label (tracked later)
            n_seizures, intervals = summary[fname]
            value = LabelValue.SEIZURE if n_seizures > 0 else LabelValue.BACKGROUND
            events = tuple(SeizureInterval(start_seconds=s, end_seconds=e) for s, e in intervals)
            label_id = mint_identity("dataset_label", {
                "recording_id": rec.recording_id, "scheme": self.label_scheme.value,
                "value": value.value}).id
            labels.append(LabelRecord(
                label_id=label_id, recording_id=rec.recording_id, scheme=self.label_scheme,
                value=value, n_events=len(events), events=events,
                source_reference=fname))
        return labels


def connector_for(source: DatasetSource, storage: DatasetStorageManager) -> RealDatasetConnector:
    if source == DatasetSource.CHB_MIT:
        return ChbMitConnector(storage)
    return EdfDirectoryConnector(storage, source)


__all__ = [
    "ConnectorResult", "parse_chb_summary", "RealDatasetConnector", "EdfDirectoryConnector",
    "ChbMitConnector", "connector_for",
]
