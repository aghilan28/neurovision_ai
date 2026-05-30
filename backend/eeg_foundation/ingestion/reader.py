"""Real EEG file ingestion via MNE-Python (the industry-standard reader).

This module reads **actual files** — there are no mock files, synthetic
placeholders, or hand-rolled parsers here. Each supported format is loaded by the
appropriate MNE reader, and the requested facts are extracted:

  file size · format · channel count · sampling frequency · duration · channel
  names · annotations · recording start time · source-reported metadata.

Reading never raises to the caller: a corrupted/unreadable/unsupported file yields
a ``ParsedEEG`` with ``parse_ok=False`` and an ``error`` string, so the validation
engine can turn it into a structured finding (P1-C) rather than an exception.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import sha256_of_file  # allowed: backend -> ml

from ..models.domain import EEGChannelType, EEGFormat
from .formats import detect_format

# Import MNE with warnings suppressed so a library-internal DeprecationWarning at
# import time cannot trip the repository's strict warning gate.
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import mne  # type: ignore

    mne.set_log_level("ERROR")


# SI unit reported per normalized channel type (MNE stores electrical signals in V).
_UNIT_BY_TYPE: dict[EEGChannelType, str] = {
    EEGChannelType.EEG: "V", EEGChannelType.EOG: "V", EEGChannelType.ECG: "V",
    EEGChannelType.EMG: "V", EEGChannelType.SEEG: "V", EEGChannelType.ECOG: "V",
    EEGChannelType.BIO: "V", EEGChannelType.REF: "V",
    EEGChannelType.STIM: "n/a", EEGChannelType.RESP: "", EEGChannelType.MISC: "",
    EEGChannelType.UNKNOWN: "",
}


@dataclass(frozen=True)
class ParsedChannel:
    """A channel as read from the source (label + normalized type + unit + rate)."""

    label: str
    channel_type: EEGChannelType
    unit: str
    sampling_frequency: float


@dataclass(frozen=True)
class ParsedEEG:
    """The result of attempting to ingest one real EEG file.

    Always returned (never raised). ``parse_ok`` indicates whether MNE decoded the
    file; when False, ``error`` explains why and the signal fields are empty/zero so
    downstream validation/metadata layers can still operate deterministically.
    """

    path: str
    original_filename: str
    file_size_bytes: int
    checksum_sha256: str
    detected_format: Optional[EEGFormat]
    declared_format: Optional[EEGFormat]
    parse_ok: bool
    error: Optional[str] = None
    sampling_frequency: float = 0.0
    duration_seconds: float = 0.0
    n_samples: int = 0
    channels: tuple[ParsedChannel, ...] = ()
    annotations: tuple[tuple[float, float, str], ...] = ()
    recording_start_time: Optional[str] = None
    patient_identifier: Optional[str] = None
    highpass_hz: Optional[float] = None
    lowpass_hz: Optional[float] = None
    source_metadata: dict = field(default_factory=dict)

    @property
    def n_channels(self) -> int:
        return len(self.channels)


_READERS = {
    "EDF": lambda p: mne.io.read_raw_edf(p, preload=False, verbose="ERROR"),
    "BDF": lambda p: mne.io.read_raw_bdf(p, preload=False, verbose="ERROR"),
    EEGFormat.FIF: lambda p: mne.io.read_raw_fif(p, preload=False, verbose="ERROR"),
    EEGFormat.SET: lambda p: mne.io.read_raw_eeglab(p, preload=True, verbose="ERROR"),
}


def _reader_for(fmt: EEGFormat):
    if fmt.family in ("EDF", "BDF"):
        return _READERS[fmt.family]
    return _READERS.get(fmt)


def _meas_date_iso(info) -> Optional[str]:
    md = info.get("meas_date")
    if md is None:
        return None
    try:
        return md.isoformat()
    except Exception:  # pragma: no cover - defensive
        return str(md)


def _patient_identifier(info) -> Optional[str]:
    """Extract a de-identified patient handle if the file carries one.

    We surface only a stable hospital/subject *id* (``his_id``/``id``) — never names
    or birthdates — honoring the platform's de-identification posture while still
    recording 'patient identifier (if present)'.
    """
    subj = info.get("subject_info") or {}
    for key in ("his_id", "id"):
        val = subj.get(key)
        if val not in (None, ""):
            return str(val)
    return None


def _source_metadata(info, fmt: EEGFormat) -> dict:
    """Deterministic, JSON-able summary of the metadata available in the source.

    Records which subject-info fields were present (keys only, no PHI values) and
    the acquisition parameters the reader exposed.
    """
    subj = info.get("subject_info") or {}
    return {
        "reader": "mne",
        "format": fmt.value,
        "nchan": int(info.get("nchan", 0) or 0),
        "sfreq": round(float(info.get("sfreq", 0.0) or 0.0), 6),
        "highpass": None if info.get("highpass") is None else round(float(info["highpass"]), 6),
        "lowpass": None if info.get("lowpass") is None else round(float(info["lowpass"]), 6),
        "line_freq": info.get("line_freq"),
        "meas_date": _meas_date_iso(info),
        "subject_info_fields": sorted(str(k) for k in subj.keys()),
    }


def load_eeg(path: str) -> ParsedEEG:
    """Ingest a real EEG file at ``path``; never raises (returns a ``ParsedEEG``)."""
    original_filename = os.path.basename(path)

    # File-level facts that hold even if the bytes are undecodable.
    try:
        file_size = os.path.getsize(path)
        checksum = sha256_of_file(path)
    except OSError as exc:
        return ParsedEEG(
            path=path, original_filename=original_filename, file_size_bytes=0,
            checksum_sha256="", detected_format=None, declared_format=None,
            parse_ok=False, error=f"unreadable: {exc}",
        )

    detected, declared = detect_format(path)

    if detected is None:
        return ParsedEEG(
            path=path, original_filename=original_filename, file_size_bytes=file_size,
            checksum_sha256=checksum, detected_format=None, declared_format=declared,
            parse_ok=False, error="unsupported or unrecognized EEG format",
        )

    reader = _reader_for(detected)
    if reader is None:  # pragma: no cover - all supported formats have a reader
        return ParsedEEG(
            path=path, original_filename=original_filename, file_size_bytes=file_size,
            checksum_sha256=checksum, detected_format=detected, declared_format=declared,
            parse_ok=False, error=f"no reader for format {detected.value}",
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = reader(path)
            info = raw.info
            sfreq = float(info["sfreq"])
            ch_names = list(raw.ch_names)
            ch_types = list(raw.get_channel_types())
            channels = []
            for label, ctype in zip(ch_names, ch_types):
                t = EEGChannelType.normalize(ctype)
                channels.append(ParsedChannel(
                    label=str(label), channel_type=t,
                    unit=_UNIT_BY_TYPE.get(t, ""), sampling_frequency=sfreq))
            n_samples = int(raw.n_times)
            duration = n_samples / sfreq if sfreq > 0 else 0.0
            ann = raw.annotations
            annotations = tuple(
                (float(o), float(d), str(desc))
                for o, d, desc in zip(ann.onset, ann.duration, ann.description)
            )
            parsed = ParsedEEG(
                path=path, original_filename=original_filename, file_size_bytes=file_size,
                checksum_sha256=checksum, detected_format=detected, declared_format=declared,
                parse_ok=True, error=None, sampling_frequency=sfreq,
                duration_seconds=duration, n_samples=n_samples, channels=tuple(channels),
                annotations=annotations, recording_start_time=_meas_date_iso(info),
                patient_identifier=_patient_identifier(info),
                highpass_hz=None if info.get("highpass") is None else float(info["highpass"]),
                lowpass_hz=None if info.get("lowpass") is None else float(info["lowpass"]),
                source_metadata=_source_metadata(info, detected),
            )
        return parsed
    except Exception as exc:  # corrupted/truncated/malformed -> structured, not fatal
        return ParsedEEG(
            path=path, original_filename=original_filename, file_size_bytes=file_size,
            checksum_sha256=checksum, detected_format=detected, declared_format=declared,
            parse_ok=False, error=f"{type(exc).__name__}: {exc}",
        )
