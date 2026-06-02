"""``backend/application_platform/uploads`` — EEG upload workflow (T3-D).

Accepts a real EEG file's bytes (EDF / EDF+ / BDF / BDF+), validates it from the **actual
bytes** via the reused ``eeg_foundation`` reader, extracts metadata, and prepares a
**bounded analysis segment** for the product workflow.

Why bounded: real clinical recordings are hours long (the CHB-MIT files are ~1 h / 921 600
samples), and the reused P1-P5 pipeline (filtering + ICA artifact removal + feature
extraction) is too slow on a full recording for an interactive product. The product
therefore analyses a deterministic **leading segment** (a clinical-epoch approach): the full
upload is preserved intact; only the analysis is bounded. Cropping reuses the platform's MNE
reader + the committed EDF writer (``tests`` is import-forbidden, so a tiny in-module
canonical EDF writer is used) — it never modifies Track 1/2 or any reused service.

Returns structured validation findings, never exceptions.
"""

from __future__ import annotations

import os
import tempfile
import warnings
from dataclasses import dataclass

from ml.provenance import hash_obj, sha256_of_file
from backend.eeg_foundation.ingestion.formats import detect_format
from backend.eeg_foundation.ingestion.reader import load_eeg

from ..models.domain import UploadFormat

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import mne  # type: ignore

    mne.set_log_level("ERROR")

_FORMAT_MAP = {"EDF": UploadFormat.EDF, "EDF+": UploadFormat.EDF_PLUS,
               "BDF": UploadFormat.BDF, "BDF+": UploadFormat.BDF_PLUS}


@dataclass(frozen=True)
class UploadValidation:
    ok: bool
    fmt: UploadFormat | None
    sampling_frequency: float
    n_channels: int
    duration_seconds: float
    channel_labels: tuple
    findings: tuple                         # (check, passed, detail)


def validate_eeg_bytes(content: bytes, filename: str) -> UploadValidation:
    """Validate uploaded EEG bytes from the ACTUAL file (structured findings, never raises)."""
    findings: list[tuple] = []

    def add(check, ok, detail=""):
        findings.append((check, bool(ok), detail))

    if not isinstance(content, (bytes, bytearray)) or len(content) == 0:
        add("non_empty", False, "upload content is empty")
        return UploadValidation(False, None, 0.0, 0, 0.0, (), tuple(findings))
    add("non_empty", True, f"{len(content)} bytes")

    suffix = os.path.splitext(filename)[1] or ".edf"
    tmp = tempfile.mktemp(suffix=suffix)
    try:
        with open(tmp, "wb") as fh:
            fh.write(bytes(content))
        detected, _ = detect_format(tmp)
        fmt_family = detected.family if detected else None
        supported = fmt_family in ("EDF", "BDF")
        add("supported_format", supported,
            f"detected={detected.value if detected else 'unknown'}")
        parsed = load_eeg(tmp)
        add("readable", parsed.parse_ok, parsed.error or "parsed")
        if not (supported and parsed.parse_ok):
            return UploadValidation(False, _FORMAT_MAP.get(detected.value) if detected else None,
                                    0.0, 0, 0.0, (), tuple(findings))
        add("has_channels", parsed.n_channels >= 1, f"n_channels={parsed.n_channels}")
        add("valid_sampling", 0 < parsed.sampling_frequency <= 20000,
            f"sfreq={parsed.sampling_frequency}")
        add("has_duration", parsed.duration_seconds > 0, f"dur={parsed.duration_seconds}")
        ok = all(p for _c, p, _d in findings)
        return UploadValidation(
            ok=ok, fmt=_FORMAT_MAP.get(parsed.detected_format.value) if parsed.detected_format
            else None, sampling_frequency=float(parsed.sampling_frequency),
            n_channels=int(parsed.n_channels), duration_seconds=float(parsed.duration_seconds),
            channel_labels=tuple(c.label for c in parsed.channels), findings=tuple(findings))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def prepare_bounded_segment(content: bytes, filename: str, *, analysis_seconds: float) -> tuple:
    """Crop the uploaded EEG to a leading ``analysis_seconds`` segment.

    Returns ``(segment_path, segment_fingerprint, segment_bytes)``. The full upload is left
    intact by the caller; this only produces the bounded analysis input. Falls back to the
    original bytes if cropping is unnecessary or unavailable.
    """
    suffix = os.path.splitext(filename)[1] or ".edf"
    src = tempfile.mktemp(suffix=suffix)
    with open(src, "wb") as fh:
        fh.write(bytes(content))
    keep_src = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            detected, _ = detect_format(src)
            family = detected.family if detected else "EDF"
            if family == "BDF":
                raw = mne.io.read_raw_bdf(src, preload=True, verbose="ERROR")
            else:
                raw = mne.io.read_raw_edf(src, preload=True, verbose="ERROR")
            sfreq = float(raw.info["sfreq"])
            total_s = raw.n_times / sfreq if sfreq else 0.0
            if total_s <= analysis_seconds + 1e-6:
                # already short enough — keep the original bytes (caller deletes the path)
                keep_src = True
                fp = hash_obj({"bytes": sha256_of_file(src)})
                return src, fp, len(content)
            seg = raw.copy().crop(tmax=analysis_seconds)
            data = seg.get_data()  # [C, T] volts
            ch = list(seg.ch_names)
        out = tempfile.mktemp(suffix=".edf")
        _write_minimal_edf(out, data, sfreq, ch)
        fp = hash_obj({"bytes": sha256_of_file(out)})
        return out, fp, os.path.getsize(out)
    finally:
        if not keep_src and os.path.exists(src):
            os.remove(src)


def _write_minimal_edf(path: str, data, sfreq: float, labels) -> None:
    """Write a valid EDF (16-bit) from a ``[C, T]`` array — deterministic, stdlib only.

    A self-contained canonical EDF writer (the ``tests`` EDF writer is import-forbidden from
    ``backend``). One record per second; physical range derived from the data.
    """
    import numpy as np

    data = np.asarray(data, dtype=np.float64)
    n_ch, n = data.shape
    sf = int(round(sfreq))
    n_records = max(1, n // sf)
    usable = n_records * sf
    data = data[:, :usable]
    dmin, dmax = -32768, 32767
    pmin = np.minimum(data.min(axis=1), -1e-9)
    pmax = np.maximum(data.max(axis=1), 1e-9)

    def fld(v, w):
        return str(v)[:w].ljust(w).encode("ascii", "replace")

    ns = n_ch
    header = bytearray()
    header += fld("0", 8)
    header += fld("X X X X", 80)
    header += fld("Startdate X X X X", 80)
    header += fld("01.01.21", 8)
    header += fld("00.00.00", 8)
    header += fld(256 + ns * 256, 8)
    header += fld("EDF+C", 44)
    header += fld(n_records, 8)
    header += fld("1", 8)            # record duration (s)
    header += fld(ns, 4)
    for lab in labels:
        header += fld(lab, 16)
    for _ in range(ns):
        header += fld("EEG", 80)     # transducer
    for _ in range(ns):
        header += fld("uV", 8)       # physical dimension
    for i in range(ns):
        header += fld("%.4f" % pmin[i], 8)
    for i in range(ns):
        header += fld("%.4f" % pmax[i], 8)
    for _ in range(ns):
        header += fld(dmin, 8)
    for _ in range(ns):
        header += fld(dmax, 8)
    for _ in range(ns):
        header += fld("", 80)        # prefiltering
    for _ in range(ns):
        header += fld(sf, 8)         # samples per record
    for _ in range(ns):
        header += fld("", 32)        # reserved

    scale = (dmax - dmin) / (pmax - pmin)
    digital = np.clip(np.round((data - pmin[:, None]) * scale[:, None] + dmin), dmin, dmax)
    digital = digital.astype("<i2")
    body = bytearray()
    for r in range(n_records):
        for c in range(n_ch):
            body += digital[c, r * sf:(r + 1) * sf].tobytes()
    with open(path, "wb") as fh:
        fh.write(bytes(header))
        fh.write(bytes(body))


from .duplicates import DuplicateDecision, DuplicateDetector, content_hash  # noqa: E402

__all__ = ["UploadValidation", "validate_eeg_bytes", "prepare_bounded_segment",
           "DuplicateDecision", "DuplicateDetector", "content_hash"]
