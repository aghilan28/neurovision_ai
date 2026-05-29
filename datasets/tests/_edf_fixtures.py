"""Deterministic EDF / EDF+ fixture writer for tests.

A self-contained EDF writer used *only* by the test suite to synthesize valid
EDF/EDF+ files (and deliberately malformed ones for negative tests). Keeping a
writer here means the reader is tested against bytes this repository fully
controls — there is no hidden third-party EDF dependency anywhere in V1.

The writer is deterministic: identical parameters produce byte-identical files,
which is what lets the reproducibility tests assert stable content hashes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

_MAIN_HEADER_BYTES = 256
_SIGNAL_HEADER_BYTES = 256
_EDF_ANNOTATIONS_LABEL = "EDF Annotations"


def _fmt(value: str, width: int) -> bytes:
    """Left-justify ``value`` into a fixed-width ASCII (latin-1) field."""
    encoded = value.encode("latin-1", "replace")[:width]
    return encoded.ljust(width, b" ")


@dataclass(frozen=True)
class SignalSpec:
    """Specification of one EDF data signal for the writer."""

    label: str
    sampling_rate_hz: float
    physical_min: float = -250.0
    physical_max: float = 250.0
    digital_min: int = -2048
    digital_max: int = 2047
    dimension: str = "uV"
    transducer: str = ""
    prefiltering: str = ""
    #: Optional explicit physical samples; generated deterministically if omitted.
    samples: np.ndarray | None = None


@dataclass(frozen=True)
class EdfPlusAnnotation:
    onset_seconds: float
    duration_seconds: float | None
    text: str


@dataclass
class EdfBuildSpec:
    """Full description of an EDF/EDF+ file to synthesize."""

    signals: list[SignalSpec]
    record_duration_seconds: float = 1.0
    num_records: int = 10
    patient_field: str = "X X X X"
    recording_field: str = "Startdate X X X X"
    start_date: str = "01.01.20"
    start_time: str = "00.00.00"
    edf_plus: bool = False
    discontinuous: bool = False
    annotations: list[EdfPlusAnnotation] = field(default_factory=list)


def _generate_samples(spec: SignalSpec, total: int, index: int) -> np.ndarray:
    """Deterministic synthetic EEG-like signal (sum of two sinusoids)."""
    if spec.samples is not None:
        arr = np.asarray(spec.samples, dtype=np.float64)
        if arr.size < total:
            arr = np.pad(arr, (0, total - arr.size))
        return arr[:total]
    t = np.arange(total, dtype=np.float64) / spec.sampling_rate_hz
    f1 = 10.0 + index  # alpha-ish, offset per channel for variety
    f2 = 3.0
    amp = 0.4 * (spec.physical_max - spec.physical_min) / 2.0
    return amp * (np.sin(2 * math.pi * f1 * t) + 0.3 * np.sin(2 * math.pi * f2 * t))


def _physical_to_digital(samples: np.ndarray, spec: SignalSpec) -> np.ndarray:
    denom = spec.physical_max - spec.physical_min
    gain = denom / (spec.digital_max - spec.digital_min) if denom else 1.0
    if gain == 0:
        gain = 1.0
    digital = np.round((samples - spec.physical_min) / gain + spec.digital_min)
    return np.clip(digital, spec.digital_min, spec.digital_max).astype("<i2")


def _annotation_block(
    onset: float,
    user_annotations: list[EdfPlusAnnotation],
    block_samples: int,
) -> bytes:
    """Build one record's annotation channel bytes (time-keeping TAL + user TALs)."""
    out = bytearray()
    # Time-keeping TAL: "+<onset>\x14\x14\x00"
    out += f"+{_num(onset)}".encode("latin-1") + b"\x14\x14\x00"
    for ann in user_annotations:
        out += f"+{_num(ann.onset_seconds)}".encode("latin-1")
        if ann.duration_seconds is not None:
            out += b"\x15" + _num(ann.duration_seconds).encode("latin-1")
        out += b"\x14" + ann.text.encode("utf-8") + b"\x14\x00"
    size = block_samples * 2
    if len(out) > size:
        raise ValueError("annotation block too small for the requested annotations")
    return bytes(out).ljust(size, b"\x00")


def _num(value: float) -> str:
    """Format a TAL time as a compact, deterministic decimal string."""
    if float(value).is_integer():
        return str(int(value))
    return repr(round(float(value), 6))


def build_edf_bytes(spec: EdfBuildSpec) -> bytes:
    """Serialize an :class:`EdfBuildSpec` into EDF/EDF+ bytes."""
    signals = list(spec.signals)
    total_per_signal = {
        s.label: int(round(s.sampling_rate_hz * spec.record_duration_seconds)) * spec.num_records
        for s in signals
    }
    samples_per_record = {
        s.label: int(round(s.sampling_rate_hz * spec.record_duration_seconds)) for s in signals
    }

    # Pre-generate digital data per data signal.
    digital: dict[str, np.ndarray] = {}
    for idx, s in enumerate(signals):
        phys = _generate_samples(s, total_per_signal[s.label], idx)
        digital[s.label] = _physical_to_digital(phys, s)

    annot_samples_per_record = 0
    annotation_records: list[bytes] = []
    if spec.edf_plus:
        # Determine annotation block size: record 0 carries all user annotations.
        # Compute the largest needed and pad uniformly.
        provisional = []
        for r in range(spec.num_records):
            onset = r * spec.record_duration_seconds
            users = spec.annotations if r == 0 else []
            # Build unpadded to measure size.
            tmp = bytearray()
            tmp += f"+{_num(onset)}".encode("latin-1") + b"\x14\x14\x00"
            for ann in users:
                tmp += f"+{_num(ann.onset_seconds)}".encode("latin-1")
                if ann.duration_seconds is not None:
                    tmp += b"\x15" + _num(ann.duration_seconds).encode("latin-1")
                tmp += b"\x14" + ann.text.encode("utf-8") + b"\x14\x00"
            provisional.append((onset, users, len(tmp)))
        max_bytes = max(size for _, _, size in provisional)
        annot_samples_per_record = max(1, math.ceil(max_bytes / 2))
        for onset, users, _ in provisional:
            annotation_records.append(
                _annotation_block(onset, users, annot_samples_per_record)
            )

    # --- assemble signal header table ---
    ns = len(signals) + (1 if spec.edf_plus else 0)
    header_bytes = _MAIN_HEADER_BYTES + ns * _SIGNAL_HEADER_BYTES

    reserved = ""
    if spec.edf_plus:
        reserved = "EDF+D" if spec.discontinuous else "EDF+C"

    main = bytearray()
    main += _fmt("0", 8)
    main += _fmt(spec.patient_field, 80)
    main += _fmt(spec.recording_field, 80)
    main += _fmt(spec.start_date, 8)
    main += _fmt(spec.start_time, 8)
    main += _fmt(str(header_bytes), 8)
    main += _fmt(reserved, 44)
    main += _fmt(str(spec.num_records), 8)
    main += _fmt(_num(spec.record_duration_seconds), 8)
    main += _fmt(str(ns), 4)
    assert len(main) == _MAIN_HEADER_BYTES

    labels = [s.label for s in signals]
    transducers = [s.transducer for s in signals]
    dimensions = [s.dimension for s in signals]
    pmins = [s.physical_min for s in signals]
    pmaxs = [s.physical_max for s in signals]
    dmins = [s.digital_min for s in signals]
    dmaxs = [s.digital_max for s in signals]
    prefilts = [s.prefiltering for s in signals]
    spr = [samples_per_record[s.label] for s in signals]

    if spec.edf_plus:
        labels.append(_EDF_ANNOTATIONS_LABEL)
        transducers.append("")
        dimensions.append("")
        pmins.append(-1.0)
        pmaxs.append(1.0)
        dmins.append(-32768)
        dmaxs.append(32767)
        prefilts.append("")
        spr.append(annot_samples_per_record)

    sig_header = bytearray()
    for label in labels:
        sig_header += _fmt(label, 16)
    for tr in transducers:
        sig_header += _fmt(tr, 80)
    for dim in dimensions:
        sig_header += _fmt(dim, 8)
    for pmin in pmins:
        sig_header += _fmt(_num(pmin), 8)
    for pmax in pmaxs:
        sig_header += _fmt(_num(pmax), 8)
    for dmin in dmins:
        sig_header += _fmt(str(dmin), 8)
    for dmax in dmaxs:
        sig_header += _fmt(str(dmax), 8)
    for pf in prefilts:
        sig_header += _fmt(pf, 80)
    for n in spr:
        sig_header += _fmt(str(n), 8)
    for _ in labels:
        sig_header += _fmt("", 32)
    assert len(sig_header) == ns * _SIGNAL_HEADER_BYTES

    # --- assemble data records (interleaved) ---
    data = bytearray()
    for r in range(spec.num_records):
        for s in signals:
            n = samples_per_record[s.label]
            start = r * n
            chunk = digital[s.label][start : start + n]
            data += chunk.tobytes()
        if spec.edf_plus:
            data += annotation_records[r]

    return bytes(main + sig_header + data)


def write_edf(path, spec: EdfBuildSpec) -> str:
    """Write an EDF/EDF+ file from ``spec`` and return the path (as ``str``)."""
    raw = build_edf_bytes(spec)
    with open(path, "wb") as handle:
        handle.write(raw)
    return str(path)


# --- Convenience builders ----------------------------------------------------
def standard_eeg_spec(
    *,
    channels: tuple[str, ...] = ("Fp1", "Fp2", "C3", "C4", "O1", "O2"),
    sampling_rate_hz: float = 256.0,
    duration_s: float = 10.0,
    edf_plus: bool = False,
    patient_field: str = "P-001 M 02-MAY-1951 Test_Patient",
    recording_field: str = "Startdate 02-MAR-2002 ADM-1 Tech EquipmentX",
    annotations: list[EdfPlusAnnotation] | None = None,
) -> EdfBuildSpec:
    """A clean, standard multi-channel EEG spec for the common test path."""
    record_duration = 1.0
    num_records = int(round(duration_s / record_duration))
    signals = [SignalSpec(label=ch, sampling_rate_hz=sampling_rate_hz) for ch in channels]
    return EdfBuildSpec(
        signals=signals,
        record_duration_seconds=record_duration,
        num_records=num_records,
        patient_field=patient_field if edf_plus else "Test patient plain EDF",
        recording_field=recording_field,
        start_date="02.03.02",
        start_time="14.30.00",
        edf_plus=edf_plus,
        annotations=annotations or [],
    )
