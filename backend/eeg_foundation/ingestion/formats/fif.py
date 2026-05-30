"""Real FIF (FIFF) reader (Productization P1).

A spec-compliant pure-Python reader for the Elekta/Neuromag/MNE FIFF tagged binary
format. FIFF is a sequence of big-endian tags: ``kind(i4) type(i4) size(u4) next(i4)``
followed by ``size`` data bytes. This reader walks the real tags of a real file and
extracts: number of channels (FIFF_NCHAN), sampling frequency (FIFF_SFREQ), channel
names + kinds (FIFF_CH_INFO structs), measurement date (FIFF_MEAS_DATE), and the
sample count (from FIFF_DATA_BUFFER tags). It never raises — it returns
``RawEEG(ok=False, error=...)`` on malformed content.
"""

from __future__ import annotations

import datetime
import struct
from typing import Optional

from ..raw import RawEEG, RawChannel

# FIFF tag kinds
FIFF_FILE_ID = 100
FIFF_BLOCK_START = 104
FIFF_BLOCK_END = 105
FIFF_NCHAN = 200
FIFF_SFREQ = 201
FIFF_CH_INFO = 203
FIFF_MEAS_DATE = 204
FIFF_DATA_BUFFER = 300

# FIFF data types (low bits)
FIFFT_SHORT = 2
FIFFT_INT = 3
FIFFT_FLOAT = 4
FIFFT_DOUBLE = 5
FIFFT_DAU_PACK16 = 16

_DTYPE_BYTES = {FIFFT_SHORT: 2, FIFFT_INT: 4, FIFFT_FLOAT: 4, FIFFT_DOUBLE: 8,
                FIFFT_DAU_PACK16: 2}

_CH_INFO_SIZE = 96
# channel kind codes (FIFF): 1=MEG,2=EEG,3=STIM,202=EOG,402=ECG,...
_KIND_MAP = {2: "eeg", 1: "meg", 3: "stim", 202: "eog", 402: "ecg", 502: "misc", 900: "syst"}


def is_fif(head: bytes) -> bool:
    """A FIFF file begins with a FIFF_FILE_ID tag (kind=100)."""
    if len(head) < 4:
        return False
    (kind,) = struct.unpack(">i", head[0:4])
    return kind == FIFF_FILE_ID


def _decode_date(secs: int) -> Optional[str]:
    try:
        dt = datetime.datetime.fromtimestamp(int(secs), datetime.timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except (OverflowError, OSError, ValueError):
        return None


def read_fif(path: str) -> RawEEG:
    import os
    try:
        file_size = os.path.getsize(path)
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        return RawEEG(ok=False, fmt="FIF", error=f"OS error reading file: {exc}")

    try:
        if not is_fif(data[:4]):
            return RawEEG(ok=False, fmt="FIF", file_size_bytes=file_size,
                          error="not a FIFF file (missing FIFF_FILE_ID tag)")
        nchan: Optional[int] = None
        sfreq: Optional[float] = None
        meas_date: Optional[str] = None
        ch_names: list = []
        ch_kinds: list = []
        total_samples = 0

        pos, n = 0, len(data)
        guard = 0
        while pos + 16 <= n:
            guard += 1
            if guard > 5_000_000:
                break
            kind, dtype, size, _next = struct.unpack(">iiii", data[pos:pos + 16])
            payload = data[pos + 16: pos + 16 + size]
            if len(payload) < size:
                return RawEEG(ok=False, fmt="FIF", file_size_bytes=file_size,
                              error="truncated FIFF tag (declared size exceeds file)")
            if kind == FIFF_NCHAN and size >= 4:
                (nchan,) = struct.unpack(">i", payload[:4])
            elif kind == FIFF_SFREQ and size >= 4:
                (sfreq,) = struct.unpack(">f", payload[:4])
            elif kind == FIFF_MEAS_DATE and size >= 4:
                (secs,) = struct.unpack(">i", payload[:4])
                meas_date = _decode_date(secs)
            elif kind == FIFF_CH_INFO and size >= _CH_INFO_SIZE:
                (chkind,) = struct.unpack(">i", payload[8:12])
                name = payload[80:96].split(b"\x00", 1)[0].decode("ascii", "ignore").strip()
                ch_names.append(name or f"CH{len(ch_names) + 1}")
                ch_kinds.append(_KIND_MAP.get(chkind, "eeg"))
            elif kind == FIFF_DATA_BUFFER and size > 0:
                width = _DTYPE_BYTES.get(dtype & 0xFFFF, 4)
                if nchan:
                    total_samples += (size // width) // max(1, nchan)
            pos += 16 + size

        if nchan is None or sfreq is None or sfreq <= 0:
            return RawEEG(ok=False, fmt="FIF", file_size_bytes=file_size,
                          error="missing essential FIFF metadata (nchan/sfreq)")

        # if no ch_info tags were present, synthesize labels
        if not ch_names:
            ch_names = [f"CH{i + 1}" for i in range(nchan)]
            ch_kinds = ["eeg"] * nchan

        channels = tuple(
            RawChannel(label=ch_names[i], sampling_frequency=round(float(sfreq), 6),
                       physical_dimension="", transducer="",
                       kind=ch_kinds[i] if i < len(ch_kinds) else "eeg")
            for i in range(min(nchan, len(ch_names))))
        duration = round(total_samples / sfreq, 6) if (sfreq and total_samples) else 0.0
        return RawEEG(
            ok=True, fmt="FIF", subtype="raw", channels=channels, n_samples=total_samples,
            duration_seconds=duration, recording_start=meas_date, patient_field="",
            recording_field="", annotations=(), file_size_bytes=file_size,
            extra={"nchan": nchan, "sfreq": float(sfreq)})
    except Exception as exc:
        return RawEEG(ok=False, fmt="FIF", file_size_bytes=file_size, error=f"parse error: {exc}")
