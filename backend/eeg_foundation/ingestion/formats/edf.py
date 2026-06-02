"""Real EDF / EDF+ / BDF / BDF+ reader (Productization P1).

A spec-compliant pure-Python reader for the European Data Format family:

* **EDF**  — 16-bit, ASCII header (256 bytes) + per-signal headers (256 bytes each).
* **EDF+** — EDF with an "EDF Annotations" signal carrying TALs; reserved starts EDF+C/EDF+D.
* **BDF**  — BioSemi 24-bit; version byte 0xFF + "BIOSEMI"; samples are int24 little-endian.
* **BDF+** — BDF with a "BDF Annotations" signal.

This reads the **real bytes** of a real file (header field offsets per the EDF/BDF
spec) and extracts: format/subtype, channel layout (labels, per-channel sampling
frequency, physical dimension, transducer), number of data records and record
duration, duration, recording start datetime, the raw patient/recording header
fields, and EDF+/BDF+ annotations (parsed from TALs). It never raises on malformed
content — it returns ``RawEEG(ok=False, error=...)``.

Out of scope (P1): no signal scaling, filtering, or feature extraction.
"""

from __future__ import annotations

from typing import Optional

from ..raw import RawEEG, RawChannel

_HEADER_BYTES = 256
_ANNOT_LABELS = ("EDF Annotations", "BDF Annotations")


def _atoi(b: bytes, default: int = 0) -> int:
    s = b.decode("ascii", "ignore").strip()
    try:
        return int(s)
    except ValueError:
        return default


def _atof(b: bytes, default: float = 0.0) -> float:
    s = b.decode("ascii", "ignore").strip()
    try:
        return float(s)
    except ValueError:
        return default


def _ascii(b: bytes) -> str:
    return b.decode("ascii", "ignore").strip()


def _start_datetime(date8: bytes, time8: bytes) -> Optional[str]:
    d = _ascii(date8)
    t = _ascii(time8)
    try:
        dd, mm, yy = (int(x) for x in d.split("."))
        hh, mi, ss = (int(x) for x in t.split("."))
        year = 1900 + yy if yy >= 85 else 2000 + yy
        return f"{year:04d}-{mm:02d}-{dd:02d}T{hh:02d}:{mi:02d}:{ss:02d}"
    except (ValueError, IndexError):
        return None


def _detect_family(head: bytes) -> Optional[str]:
    """Return 'BDF' or 'EDF' from the 8-byte version field, or None."""
    if len(head) < 8:
        return None
    if head[0] == 0xFF and head[1:8] == b"BIOSEMI":
        return "BDF"
    # EDF version field is '0       '
    if head[0:8].decode("ascii", "ignore").strip() == "0":
        return "EDF"
    return None


def is_edf_family(head: bytes) -> bool:
    return _detect_family(head) is not None


def _parse_tals(block: bytes) -> list:
    """Parse EDF+/BDF+ TALs from one annotation-channel record's bytes.

    Returns a list of (onset, duration, description). The first (timekeeping) TAL and
    any TAL with an empty description are skipped. Separators: 0x15 (onset/duration),
    0x14 (field/description end), 0x00 (TAL end).
    """
    out = []
    for tal in block.split(b"\x00"):
        if not tal or b"\x14" not in tal:
            continue
        try:
            head, rest = tal.split(b"\x14", 1)
        except ValueError:
            continue
        if b"\x15" in head:
            onset_b, dur_b = head.split(b"\x15", 1)
            duration = _safe_float(dur_b)
        else:
            onset_b, duration = head, 0.0
        onset = _safe_float(onset_b)
        # descriptions are the remaining 0x14-separated, non-empty tokens
        for desc in rest.split(b"\x14"):
            text = desc.decode("utf-8", "replace").strip()
            if text:
                out.append((onset, duration, text))
    return out


def _safe_float(b: bytes) -> float:
    try:
        return float(b.decode("ascii", "ignore").strip() or 0.0)
    except ValueError:
        return 0.0


def read_edf(path: str) -> RawEEG:
    """Read a real EDF/EDF+/BDF/BDF+ file into a :class:`RawEEG`."""
    import os
    try:
        file_size = os.path.getsize(path)
        with open(path, "rb") as fh:
            head = fh.read(_HEADER_BYTES)
            if len(head) < _HEADER_BYTES:
                return RawEEG(ok=False, fmt="EDF", file_size_bytes=file_size,
                              error="file shorter than a 256-byte EDF/BDF header")
            family = _detect_family(head)
            if family is None:
                return RawEEG(ok=False, fmt="UNKNOWN", file_size_bytes=file_size,
                              error="not an EDF/BDF file (bad version field)")
            bytes_per_sample = 3 if family == "BDF" else 2

            patient_field = _ascii(head[8:88])
            recording_field = _ascii(head[88:168])
            recording_start = _start_datetime(head[168:176], head[176:184])
            header_bytes = _atoi(head[184:192], default=_HEADER_BYTES)
            reserved = _ascii(head[192:236]).upper()
            n_records = _atoi(head[236:244], default=-1)
            record_duration = _atof(head[244:252], default=0.0)
            ns = _atoi(head[252:256], default=0)
            if ns <= 0:
                return RawEEG(ok=False, fmt=family, file_size_bytes=file_size,
                              error=f"invalid signal count ns={ns}")

            sig = fh.read(ns * 256)
            if len(sig) < ns * 256:
                return RawEEG(ok=False, fmt=family, file_size_bytes=file_size,
                              error="truncated signal-header section")

        # subtype + format
        plus = reserved.startswith("EDF+") or reserved.startswith("BDF+") \
            or "EDF+C" in reserved or "EDF+D" in reserved \
            or "BDF+C" in reserved or "BDF+D" in reserved
        labels = [_ascii(sig[i * 16:(i + 1) * 16]) for i in range(ns)]
        has_annot = any(lbl in _ANNOT_LABELS for lbl in labels)
        is_plus = plus or has_annot
        if family == "BDF":
            fmt = "BDF+" if is_plus else "BDF"
        else:
            fmt = "EDF+" if is_plus else "EDF"
        subtype = ("discontinuous" if (reserved.endswith("D") or "+D" in reserved)
                   else ("continuous" if is_plus else ""))

        # per-signal header fields, addressed by explicit cumulative byte offsets
        # (each field is laid out as ns repetitions of a fixed width).
        off_label = 0
        off_trans = off_label + 16
        off_pdim = off_trans + 80
        off_pmin = off_pdim + 8
        off_pmax = off_pmin + 8
        off_dmin = off_pmax + 8
        off_dmax = off_dmin + 8
        off_pref = off_dmax + 8
        off_nsmp = off_pref + 80

        def fields(off, width):
            base = ns * off
            return [sig[base + i * width: base + (i + 1) * width] for i in range(ns)]

        transducers = [_ascii(x) for x in fields(off_trans, 80)]
        phys_dims = [_ascii(x) for x in fields(off_pdim, 8)]
        nsamp_per_record = [_atoi(x, 0) for x in fields(off_nsmp, 8)]

        if record_duration <= 0.0:
            return RawEEG(ok=False, fmt=fmt, file_size_bytes=file_size,
                          error=f"invalid record duration {record_duration}")

        # channels
        channels = []
        annot_index = None
        for i in range(ns):
            is_ann = labels[i] in _ANNOT_LABELS
            if is_ann and annot_index is None:
                annot_index = i
            sf = (nsamp_per_record[i] / record_duration) if record_duration else 0.0
            channels.append(RawChannel(
                label=labels[i], sampling_frequency=round(sf, 6),
                physical_dimension=phys_dims[i], transducer=transducers[i],
                kind="annotation" if is_ann else "eeg"))

        bytes_per_record = sum(nsamp_per_record) * bytes_per_sample
        actual_data_bytes = max(0, file_size - header_bytes)
        if n_records < 0 and bytes_per_record > 0:
            n_records = actual_data_bytes // bytes_per_record
        expected_data_bytes = (n_records * bytes_per_record) if n_records >= 0 else None
        duration_seconds = round((n_records * record_duration), 6) if n_records >= 0 else 0.0

        # representative samples per signal channel (first non-annotation channel)
        signal_idxs = [i for i in range(ns) if channels[i].kind != "annotation"]
        n_samples = (nsamp_per_record[signal_idxs[0]] * n_records) if (signal_idxs and n_records >= 0) else 0

        # annotations (EDF+/BDF+): read just the annotation channel slices per record
        annotations = []
        if annot_index is not None and n_records and bytes_per_record > 0:
            annotations = _read_annotations(
                path, header_bytes, nsamp_per_record, bytes_per_sample, annot_index,
                n_records, bytes_per_record)

        annot_types = tuple(sorted({a["description"] for a in annotations}))
        return RawEEG(
            ok=True, fmt=fmt, subtype=subtype, channels=tuple(channels), n_samples=n_samples,
            duration_seconds=duration_seconds, recording_start=recording_start,
            patient_field=patient_field, recording_field=recording_field,
            annotations=tuple(annotations), file_size_bytes=file_size,
            expected_data_bytes=expected_data_bytes, actual_data_bytes=actual_data_bytes,
            extra={"n_records": n_records, "record_duration": record_duration,
                   "bytes_per_sample": bytes_per_sample, "header_bytes": header_bytes,
                   "annotation_types": list(annot_types)})
    except OSError as exc:
        return RawEEG(ok=False, fmt="EDF", error=f"OS error reading file: {exc}")
    except Exception as exc:  # never raise; report as a finding
        return RawEEG(ok=False, fmt="EDF", error=f"parse error: {exc}")


def _read_annotations(path, header_bytes, nsamp_per_record, bps, annot_index, n_records,
                      bytes_per_record) -> list:
    """Read + parse TALs from the annotation channel of every data record."""
    # byte offset of the annotation channel within a single data record
    offset_in_record = sum(nsamp_per_record[:annot_index]) * bps
    ann_bytes = nsamp_per_record[annot_index] * bps
    out = []
    with open(path, "rb") as fh:
        for r in range(n_records):
            rec_start = header_bytes + r * bytes_per_record + offset_in_record
            fh.seek(rec_start)
            block = fh.read(ann_bytes)
            if len(block) < ann_bytes:
                break
            for onset, duration, desc in _parse_tals(block):
                out.append({"onset_seconds": onset, "duration_seconds": duration,
                            "description": desc})
    return out
