"""Pure-Python EDF / EDF+ reader.

This module implements a deterministic reader for the European Data Format (EDF)
and its EDF+ extension, using only the Python standard library and NumPy. It is
intentionally dependency-free of any third-party EDF library so that the parsing
behaviour is fully owned, auditable, and reproducible (AP-3/AP-6, NR-9/NR-10).

Format reference (the relevant, stable facts used here)
-------------------------------------------------------
EDF is a simple binary container:

* A fixed **256-byte main header** with ASCII fields (version, patient id,
  recording id, start date/time, header size, reserved, number of data records,
  data-record duration, and signal count ``ns``).
* A **256-byte-per-signal header block** (``ns`` signals), each field stored as
  ``ns`` consecutive fixed-width ASCII columns (labels, transducer, physical
  dimension, physical/digital min/max, prefiltering, samples-per-record, reserved).
* **Data records**: ``num_data_records`` records, each holding, per signal,
  ``samples_per_record[i]`` little-endian 16-bit signed integers.

Physical (calibrated) values are recovered per signal via the EDF linear scaling:

    physical = (digital - digital_min) * (physical_max - physical_min)
               / (digital_max - digital_min) + physical_min

EDF+ adds an ``"EDF Annotations"`` signal carrying UTF-8 Time-stamped Annotation
Lists (TALs) and marks continuity (``"EDF+C"``) or discontinuity (``"EDF+D"``) in
the reserved field. Both are read here.

This reader **does not modify** the signal in any way (no filtering, scaling
choices, or resampling) — that is the exclusive responsibility of
``preprocessing/`` (DSP leaf). The reader only decodes what the file contains.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# --- Format constants --------------------------------------------------------
MAIN_HEADER_BYTES = 256
SIGNAL_HEADER_BYTES = 256
BYTES_PER_SAMPLE = 2  # EDF stores 16-bit signed integers
EDF_ANNOTATIONS_LABEL = "EDF Annotations"

# TAL byte delimiters (EDF+ spec)
_TAL_ONSET_DURATION_SEP = 0x15  # separates onset from duration
_TAL_TEXT_SEP = 0x14  # separates onset/duration from text and texts from each other
_TAL_END = 0x00  # terminates a TAL

#: Reader version. Bump via a recorded governance decision (NR-5); recorded on
#: artifacts for traceability/reproducibility (AP-5/AP-6).
EDF_READER_VERSION = "1.0.0"


class EdfReadError(ValueError):
    """Raised when a file cannot be parsed as EDF/EDF+.

    Carries a stable ``code`` so callers (e.g. the ingestion pipeline / validator)
    can translate a parse failure into a structured validation issue rather than
    leaking a raw exception.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class EdfSignalHeader:
    """Decoded per-signal header fields (one EDF signal)."""

    label: str
    transducer: str
    physical_dimension: str
    physical_min: float
    physical_max: float
    digital_min: int
    digital_max: int
    prefiltering: str
    samples_per_record: int
    reserved: str

    @property
    def is_annotation(self) -> bool:
        return self.label.strip() == EDF_ANNOTATIONS_LABEL

    @property
    def gain(self) -> float:
        """Physical-per-digital scaling factor (1.0 if the digital range is degenerate)."""
        denom = self.digital_max - self.digital_min
        if denom == 0:
            return 1.0
        return (self.physical_max - self.physical_min) / denom


@dataclass(frozen=True, slots=True)
class EdfFileHeader:
    """Decoded EDF main header plus the list of signal headers."""

    version_field: str
    patient_field: str
    recording_field: str
    start_date: str
    start_time: str
    header_bytes: int
    reserved: str
    num_data_records: int
    record_duration_seconds: float
    num_signals: int
    signal_headers: tuple[EdfSignalHeader, ...]

    @property
    def is_edf_plus(self) -> bool:
        return self.reserved.strip().upper().startswith("EDF+")

    @property
    def is_discontinuous(self) -> bool:
        return self.reserved.strip().upper().startswith("EDF+D")

    @property
    def record_size_samples(self) -> int:
        return sum(h.samples_per_record for h in self.signal_headers)

    @property
    def record_size_bytes(self) -> int:
        return self.record_size_samples * BYTES_PER_SAMPLE


@dataclass(frozen=True, slots=True)
class EdfReading:
    """The full result of reading an EDF/EDF+ file.

    ``signals`` maps each *data* channel's canonical-position label to its physical
    samples as a contiguous ``float64`` array (records concatenated in order).
    The annotation channel is excluded from ``signals`` and surfaced via
    ``annotations`` instead. ``signal_order`` preserves on-disk channel order.
    """

    header: EdfFileHeader
    signal_order: tuple[str, ...]
    signals: dict[str, np.ndarray]
    annotations: tuple[tuple[float, float | None, str], ...] = ()
    record_onsets: tuple[float, ...] = ()
    extra: dict[str, object] = field(default_factory=dict)

    @property
    def num_data_records(self) -> int:
        return self.header.num_data_records

    def duration_seconds(self) -> float:
        return self.header.num_data_records * self.header.record_duration_seconds


# --- Low-level field decoding ------------------------------------------------
def _decode_ascii(raw: bytes) -> str:
    """Decode an EDF ASCII header field, tolerant of non-strict bytes.

    EDF headers are specified as ASCII; some real-world files include Latin-1
    characters. We decode permissively (latin-1 never raises) and strip trailing
    padding so the decode is deterministic and never crashes ingestion.
    """
    return raw.decode("latin-1").strip()


def _parse_int_field(raw: bytes, field_name: str) -> int:
    text = _decode_ascii(raw)
    try:
        return int(text)
    except ValueError as exc:
        raise EdfReadError(
            "HEADER_FIELD_NOT_INT",
            f"expected integer in header field '{field_name}', got {text!r}",
        ) from exc


def _parse_float_field(raw: bytes, field_name: str) -> float:
    text = _decode_ascii(raw)
    try:
        return float(text)
    except ValueError as exc:
        raise EdfReadError(
            "HEADER_FIELD_NOT_FLOAT",
            f"expected number in header field '{field_name}', got {text!r}",
        ) from exc


def _parse_main_header(buf: bytes) -> tuple[EdfFileHeader, list[EdfSignalHeader]]:
    """Parse the 256-byte main header and the per-signal header block."""
    if len(buf) < MAIN_HEADER_BYTES:
        raise EdfReadError(
            "HEADER_TOO_SHORT",
            f"file shorter than the {MAIN_HEADER_BYTES}-byte EDF main header",
        )

    version_field = _decode_ascii(buf[0:8])
    patient_field = _decode_ascii(buf[8:88])
    recording_field = _decode_ascii(buf[88:168])
    start_date = _decode_ascii(buf[168:176])
    start_time = _decode_ascii(buf[176:184])
    header_bytes = _parse_int_field(buf[184:192], "num_header_bytes")
    reserved = _decode_ascii(buf[192:236])
    num_data_records = _parse_int_field(buf[236:244], "num_data_records")
    record_duration = _parse_float_field(buf[244:252], "record_duration")
    num_signals = _parse_int_field(buf[252:256], "num_signals")

    if num_signals < 0:
        raise EdfReadError("BAD_SIGNAL_COUNT", f"negative signal count {num_signals}")

    expected_header_bytes = MAIN_HEADER_BYTES + num_signals * SIGNAL_HEADER_BYTES
    if len(buf) < expected_header_bytes:
        raise EdfReadError(
            "SIGNAL_HEADER_TRUNCATED",
            f"file too short for {num_signals} signal headers "
            f"(need {expected_header_bytes} bytes, have {len(buf)})",
        )

    sig_headers = _parse_signal_headers(buf, num_signals)

    header = EdfFileHeader(
        version_field=version_field,
        patient_field=patient_field,
        recording_field=recording_field,
        start_date=start_date,
        start_time=start_time,
        header_bytes=header_bytes,
        reserved=reserved,
        num_data_records=num_data_records,
        record_duration_seconds=record_duration,
        num_signals=num_signals,
        signal_headers=tuple(sig_headers),
    )
    return header, sig_headers


def _column(buf: bytes, base: int, index: int, width: int) -> bytes:
    start = base + index * width
    return buf[start : start + width]


def _parse_signal_headers(buf: bytes, ns: int) -> list[EdfSignalHeader]:
    """Decode the per-signal header block (each field is ``ns`` fixed-width columns)."""
    base = MAIN_HEADER_BYTES
    # Field widths in EDF signal-header order.
    w_label, w_trans, w_dim = 16, 80, 8
    w_pmin, w_pmax, w_dmin, w_dmax = 8, 8, 8, 8
    w_prefilt, w_nsamp, w_reserved = 80, 8, 32

    off_label = base
    off_trans = off_label + ns * w_label
    off_dim = off_trans + ns * w_trans
    off_pmin = off_dim + ns * w_dim
    off_pmax = off_pmin + ns * w_pmin
    off_dmin = off_pmax + ns * w_pmax
    off_dmax = off_dmin + ns * w_dmin
    off_prefilt = off_dmax + ns * w_dmax
    off_nsamp = off_prefilt + ns * w_prefilt
    off_reserved = off_nsamp + ns * w_nsamp

    headers: list[EdfSignalHeader] = []
    for i in range(ns):
        label = _decode_ascii(_column(buf, off_label, i, w_label))
        transducer = _decode_ascii(_column(buf, off_trans, i, w_trans))
        dimension = _decode_ascii(_column(buf, off_dim, i, w_dim))
        pmin = _parse_float_field(_column(buf, off_pmin, i, w_pmin), f"physical_min[{i}]")
        pmax = _parse_float_field(_column(buf, off_pmax, i, w_pmax), f"physical_max[{i}]")
        dmin = _parse_int_field(_column(buf, off_dmin, i, w_dmin), f"digital_min[{i}]")
        dmax = _parse_int_field(_column(buf, off_dmax, i, w_dmax), f"digital_max[{i}]")
        prefilt = _decode_ascii(_column(buf, off_prefilt, i, w_prefilt))
        nsamp = _parse_int_field(_column(buf, off_nsamp, i, w_nsamp), f"samples_per_record[{i}]")
        reserved = _decode_ascii(_column(buf, off_reserved, i, w_reserved))

        if nsamp < 0:
            raise EdfReadError(
                "BAD_SAMPLES_PER_RECORD",
                f"signal {i} ('{label}') has negative samples-per-record {nsamp}",
            )
        headers.append(
            EdfSignalHeader(
                label=label,
                transducer=transducer,
                physical_dimension=dimension,
                physical_min=pmin,
                physical_max=pmax,
                digital_min=dmin,
                digital_max=dmax,
                prefiltering=prefilt,
                samples_per_record=nsamp,
                reserved=reserved,
            )
        )
    return headers


def read_edf_header(path: str) -> EdfFileHeader:
    """Read and decode only the header of an EDF/EDF+ file (no signal data).

    This is the fast path used by discovery/validation when the signal samples are
    not needed. Raises :class:`EdfReadError` if the header cannot be parsed.
    """
    with open(path, "rb") as handle:
        prefix = handle.read(MAIN_HEADER_BYTES)
        if len(prefix) < MAIN_HEADER_BYTES:
            raise EdfReadError(
                "HEADER_TOO_SHORT",
                f"file shorter than the {MAIN_HEADER_BYTES}-byte EDF main header",
            )
        ns = _parse_int_field(prefix[252:256], "num_signals")
        if ns < 0:
            raise EdfReadError("BAD_SIGNAL_COUNT", f"negative signal count {ns}")
        rest = handle.read(ns * SIGNAL_HEADER_BYTES)
    header, _ = _parse_main_header(prefix + rest)
    return header


def _resolve_num_records(header: EdfFileHeader, data_byte_len: int) -> int:
    """Determine the usable number of data records.

    Handles ``num_data_records == -1`` (unknown, allowed by EDF) by computing the
    count from the available data length. Never reads past the available bytes.
    """
    record_bytes = header.record_size_bytes
    if record_bytes == 0:
        return 0
    computed = data_byte_len // record_bytes
    declared = header.num_data_records
    if declared < 0:
        return computed
    # Trust the smaller of declared vs available so we never read out of bounds.
    return min(declared, computed)


def _deinterleave_signals(
    data: np.ndarray,
    header: EdfFileHeader,
    usable_records: int,
) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray]]:
    """Split interleaved records into per-signal digital arrays.

    Returns ``(digital_by_index, raw_int16_by_index)`` for non-annotation signals.
    The annotation channel's int16 view is also returned (used to recover its raw
    bytes) keyed by its signal index.
    """
    record_size = header.record_size_samples
    # Offsets of each signal within a single record.
    offsets: list[int] = []
    cursor = 0
    for h in header.signal_headers:
        offsets.append(cursor)
        cursor += h.samples_per_record

    grid = data[: usable_records * record_size].reshape(usable_records, record_size)

    digital_by_index: dict[int, np.ndarray] = {}
    for idx, h in enumerate(header.signal_headers):
        start = offsets[idx]
        end = start + h.samples_per_record
        # Concatenate this signal's columns across all records -> 1-D series.
        digital_by_index[idx] = grid[:, start:end].reshape(-1)
    return digital_by_index, digital_by_index


def _digital_to_physical(digital: np.ndarray, h: EdfSignalHeader) -> np.ndarray:
    """Apply EDF linear calibration to recover physical units as ``float64``."""
    d = digital.astype(np.float64)
    return (d - h.digital_min) * h.gain + h.physical_min


def _parse_tal_block(block: bytes) -> list[tuple[float, float | None, str]]:
    """Parse one annotation channel record's bytes into TAL entries.

    Each TAL is terminated by a NUL (``0x00``). Within a TAL, the onset (and
    optional duration after ``0x15``) precede ``0x14``-separated annotation texts.
    The leading "time-keeping" TAL of each record (empty text) is preserved as an
    entry with empty text so record onsets can be recovered for EDF+D.
    """
    results: list[tuple[float, float | None, str]] = []
    for tal in block.split(bytes([_TAL_END])):
        if not tal:
            continue
        parts = tal.split(bytes([_TAL_TEXT_SEP]))
        timing = parts[0]
        if bytes([_TAL_ONSET_DURATION_SEP]) in timing:
            onset_b, dur_b = timing.split(bytes([_TAL_ONSET_DURATION_SEP]), 1)
            try:
                duration: float | None = float(dur_b.decode("latin-1")) if dur_b else None
            except ValueError:
                duration = None
        else:
            onset_b, duration = timing, None
        onset_text = onset_b.decode("latin-1").strip()
        if not onset_text:
            continue
        try:
            onset = float(onset_text)
        except ValueError:
            continue
        texts = [p.decode("utf-8", "replace") for p in parts[1:]]
        non_empty = [t for t in texts if t]
        if non_empty:
            for t in non_empty:
                results.append((onset, duration, t))
        else:
            # Time-keeping TAL (record onset marker), preserved with empty text.
            results.append((onset, duration, ""))
    return results


def _extract_annotations(
    raw_bytes: bytes,
    header: EdfFileHeader,
    usable_records: int,
) -> tuple[list[tuple[float, float | None, str]], list[float]]:
    """Recover EDF+ annotations and per-record onsets from the annotation channel."""
    annot_indices = [i for i, h in enumerate(header.signal_headers) if h.is_annotation]
    if not annot_indices:
        return [], []

    record_bytes = header.record_size_bytes
    # Byte offset of each signal within a record.
    byte_offsets: list[int] = []
    cursor = 0
    for h in header.signal_headers:
        byte_offsets.append(cursor)
        cursor += h.samples_per_record * BYTES_PER_SAMPLE

    annotations: list[tuple[float, float | None, str]] = []
    record_onsets: list[float] = []
    for r in range(usable_records):
        record_start = r * record_bytes
        for idx in annot_indices:
            seg_start = record_start + byte_offsets[idx]
            seg_end = seg_start + header.signal_headers[idx].samples_per_record * BYTES_PER_SAMPLE
            block = raw_bytes[seg_start:seg_end]
            tals = _parse_tal_block(block)
            for onset, duration, text in tals:
                if text:
                    annotations.append((onset, duration, text))
                elif idx == annot_indices[0]:
                    # First annotation channel carries the record time-keeping TAL.
                    record_onsets.append(onset)
    return annotations, record_onsets


def read_edf(
    path: str,
    *,
    load_signals: bool = True,
    materialize_signals: bool = True,
) -> EdfReading:
    """Read an EDF/EDF+ file into an :class:`EdfReading`.

    Parameters
    ----------
    path:
        Filesystem path to the EDF/EDF+ file.
    load_signals:
        When ``False``, only the header is parsed; ``signals`` and ``annotations``
        are empty (fast header-only path for discovery / integrity).
    materialize_signals:
        When ``True`` (and ``load_signals`` is ``True``), decode every data
        channel into a physical ``float64`` array. When ``False``, the data
        section is still scanned for EDF+ annotations but the (potentially large)
        float signal arrays are **not** built — the efficient path for ingestion,
        which needs annotations + metadata but not the samples themselves.

    Raises
    ------
    EdfReadError
        If the file cannot be parsed as EDF/EDF+.
    """
    with open(path, "rb") as handle:
        raw = handle.read()

    header, sig_headers = _parse_main_header(raw)
    header_len = MAIN_HEADER_BYTES + header.num_signals * SIGNAL_HEADER_BYTES
    data_bytes = raw[header_len:]

    signals: dict[str, np.ndarray] = {}
    signal_order = tuple(h.label.strip() for h in sig_headers)

    if not load_signals or header.record_size_samples == 0:
        return EdfReading(
            header=header,
            signal_order=signal_order,
            signals=signals,
            annotations=(),
            record_onsets=(),
        )

    usable_records = _resolve_num_records(header, len(data_bytes))

    if materialize_signals:
        int16 = np.frombuffer(
            data_bytes[: usable_records * header.record_size_bytes],
            dtype="<i2",
        )
        digital_by_index, _ = _deinterleave_signals(int16, header, usable_records)
        for idx, h in enumerate(sig_headers):
            if h.is_annotation:
                continue
            signals[h.label.strip()] = _digital_to_physical(digital_by_index[idx], h)

    annotations, record_onsets = _extract_annotations(data_bytes, header, usable_records)

    return EdfReading(
        header=header,
        signal_order=signal_order,
        signals=signals,
        annotations=tuple(annotations),
        record_onsets=tuple(record_onsets),
        extra={"usable_records": usable_records},
    )
