"""Real SET (EEGLAB) reader (Productization P1).

An EEGLAB ``.set`` file is a MATLAB Level-5 MAT-file containing the ``EEG`` struct.
This is a spec-compliant pure-Python reader for the MAT-file v5 container: it parses
the 128-byte header, walks the data elements (handling the small-element format and
``miCOMPRESSED`` via zlib), and reconstructs numeric / char / struct / cell arrays. It
then extracts EEG metadata: ``nbchan``, ``srate``, ``pnts``, ``xmin``/``xmax``,
channel labels (``chanlocs.labels``), and event types (``event.type``). It never
raises — it returns ``RawEEG(ok=False, error=...)`` on malformed content.
"""

from __future__ import annotations

import struct
import zlib
from typing import Optional

import numpy as np

from ..raw import RawEEG, RawChannel

# MAT-file data types
miINT8, miUINT8, miINT16, miUINT16, miINT32, miUINT32 = 1, 2, 3, 4, 5, 6
miSINGLE, miDOUBLE, miINT64, miUINT64 = 7, 9, 12, 13
miMATRIX, miCOMPRESSED, miUTF8 = 14, 15, 16

# mx array classes
mxCELL, mxSTRUCT, mxOBJECT, mxCHAR, mxSPARSE, mxDOUBLE, mxSINGLE = 1, 2, 3, 4, 5, 6, 7
mxINT8, mxUINT8, mxINT16, mxUINT16, mxINT32, mxUINT32 = 8, 9, 10, 11, 12, 13

_NUMERIC_DTYPE = {
    miINT8: "i1", miUINT8: "u1", miINT16: "i2", miUINT16: "u2", miINT32: "i4",
    miUINT32: "u4", miSINGLE: "f4", miDOUBLE: "f8", miINT64: "i8", miUINT64: "u8",
}


def is_set(head: bytes) -> bool:
    """A MAT-file v5 starts with the text 'MATLAB 5.0 MAT-file'."""
    return head[:19] == b"MATLAB 5.0 MAT-file"


class _MatError(Exception):
    pass


def _read_tag(buf: bytes, pos: int, endian: str):
    """Return (dtype, nbytes, data_start, next_pos). Handles the small-element format."""
    if pos + 8 > len(buf):
        raise _MatError("unexpected end of MAT data (tag)")
    (raw,) = struct.unpack(endian + "I", buf[pos:pos + 4])
    small = (raw >> 16) & 0xFFFF
    if small != 0:
        # small element format: bytes [pos:pos+2]=type, [pos+2:pos+4]=nbytes, data in next 4
        dtype = raw & 0xFFFF
        nbytes = small
        return dtype, nbytes, pos + 4, pos + 8
    dtype = raw
    (nbytes,) = struct.unpack(endian + "I", buf[pos + 4:pos + 8])
    data_start = pos + 8
    padded = nbytes + ((8 - (nbytes % 8)) % 8)
    return dtype, nbytes, data_start, data_start + padded


def _read_element(buf: bytes, pos: int, endian: str):
    """Read one data element; return (value, next_pos)."""
    dtype, nbytes, ds, np_ = _read_tag(buf, pos, endian)
    data = buf[ds:ds + nbytes]
    if dtype == miMATRIX:
        return _read_matrix(data, endian), np_
    if dtype == miCOMPRESSED:
        raw = zlib.decompress(data)
        value, _ = _read_element(raw, 0, endian)
        return value, np_
    if dtype in _NUMERIC_DTYPE:
        arr = np.frombuffer(data, dtype=endian + _NUMERIC_DTYPE[dtype])
        return arr, np_
    if dtype in (miUTF8, miINT8, miUINT8):
        return data, np_
    return data, np_


def _read_subelement(buf: bytes, pos: int, endian: str):
    dtype, nbytes, ds, np_ = _read_tag(buf, pos, endian)
    return dtype, buf[ds:ds + nbytes], np_


def _read_matrix(payload: bytes, endian: str):
    """Reconstruct a miMATRIX element into a Python value."""
    pos = 0
    # 1. array flags
    _, flags, pos = _read_subelement(payload, pos, endian)
    cls = flags[0] if flags else 0
    # 2. dimensions
    _, dim_bytes, pos = _read_subelement(payload, pos, endian)
    dims = list(np.frombuffer(dim_bytes, dtype=endian + "i4")) if dim_bytes else []
    # 3. name
    _, name_bytes, pos = _read_subelement(payload, pos, endian)
    _name = name_bytes.split(b"\x00", 1)[0].decode("ascii", "ignore")

    if cls == mxCHAR:
        dt, cbytes, pos = _read_subelement(payload, pos, endian)
        if dt in (miUTF8, miINT8, miUINT8):
            return cbytes.split(b"\x00", 1)[0].decode("utf-8", "ignore")
        if dt == miUINT16:
            arr = np.frombuffer(cbytes, dtype=endian + "u2")
            return "".join(chr(int(x)) for x in arr).rstrip("\x00")
        return cbytes.decode("ascii", "ignore")

    if cls in (mxDOUBLE, mxSINGLE, mxINT8, mxUINT8, mxINT16, mxUINT16, mxINT32, mxUINT32):
        dt, nbytes, ds, _ = _read_tag(payload, pos, endian)
        vals = payload[ds:ds + nbytes]
        npdt = _NUMERIC_DTYPE.get(dt, "f8")
        arr = np.frombuffer(vals, dtype=endian + npdt)
        return arr

    if cls == mxSTRUCT:
        # field-name length
        _, fnl_bytes, pos = _read_subelement(payload, pos, endian)
        field_len = int(np.frombuffer(fnl_bytes, dtype=endian + "i4")[0]) if fnl_bytes else 32
        # field names
        _, fn_bytes, pos = _read_subelement(payload, pos, endian)
        n_fields = len(fn_bytes) // field_len if field_len else 0
        field_names = []
        for i in range(n_fields):
            raw = fn_bytes[i * field_len:(i + 1) * field_len]
            field_names.append(raw.split(b"\x00", 1)[0].decode("ascii", "ignore"))
        n_elems = int(np.prod(dims)) if dims else 1
        n_elems = max(1, n_elems)
        records = []
        for _e in range(n_elems):
            rec = {}
            for fname in field_names:
                value, pos = _read_element(payload, pos, endian)
                rec[fname] = value
            records.append(rec)
        return {"__struct__": True, "fields": field_names, "records": records, "dims": dims}

    if cls == mxCELL:
        n_elems = int(np.prod(dims)) if dims else 0
        cells = []
        for _e in range(max(0, n_elems)):
            value, pos = _read_element(payload, pos, endian)
            cells.append(value)
        return cells

    return None


def _scalar(value, default=0.0) -> float:
    try:
        if isinstance(value, np.ndarray) and value.size:
            return float(value.reshape(-1)[0])
        if isinstance(value, (int, float)):
            return float(value)
    except (TypeError, ValueError):
        pass
    return default


def _as_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, np.ndarray) and value.dtype.kind in "iuf" and value.size:
        try:
            return "".join(chr(int(x)) for x in value.reshape(-1)).rstrip("\x00")
        except ValueError:
            return ""
    return ""


def read_set(path: str) -> RawEEG:
    import os
    try:
        file_size = os.path.getsize(path)
        with open(path, "rb") as fh:
            buf = fh.read()
    except OSError as exc:
        return RawEEG(ok=False, fmt="SET", error=f"OS error reading file: {exc}")

    try:
        if not is_set(buf[:19]):
            return RawEEG(ok=False, fmt="SET", file_size_bytes=file_size,
                          error="not a MATLAB 5.0 MAT-file (EEGLAB .set)")
        endian = "<" if buf[126:128] == b"IM" else ">"
        # top-level element (the EEG struct, possibly compressed)
        value, _ = _read_element(buf, 128, endian)
        eeg = _find_eeg_struct(value)
        if eeg is None:
            return RawEEG(ok=False, fmt="SET", file_size_bytes=file_size,
                          error="no EEG struct found in .set file")

        nbchan = int(_scalar(eeg.get("nbchan"), 0))
        srate = _scalar(eeg.get("srate"), 0.0)
        pnts = int(_scalar(eeg.get("pnts"), 0))
        xmax = _scalar(eeg.get("xmax"), 0.0)
        xmin = _scalar(eeg.get("xmin"), 0.0)

        labels = _channel_labels(eeg.get("chanlocs"))
        if nbchan <= 0 and labels:
            nbchan = len(labels)
        if not labels:
            labels = [f"CH{i + 1}" for i in range(max(0, nbchan))]

        if srate <= 0:
            return RawEEG(ok=False, fmt="SET", file_size_bytes=file_size,
                          error="missing/invalid sampling rate (srate) in .set")

        duration = round(pnts / srate, 6) if (pnts and srate) else round(max(0.0, xmax - xmin), 6)
        channels = tuple(RawChannel(label=labels[i], sampling_frequency=round(float(srate), 6),
                                    physical_dimension="uV", transducer="", kind="eeg")
                         for i in range(min(nbchan, len(labels))))
        annotations = _events_to_annotations(eeg.get("event"), srate)
        return RawEEG(
            ok=True, fmt="SET", subtype="eeglab", channels=channels, n_samples=pnts,
            duration_seconds=duration, recording_start=None, patient_field="",
            recording_field=_as_text(eeg.get("setname")), annotations=tuple(annotations),
            file_size_bytes=file_size,
            extra={"nbchan": nbchan, "srate": float(srate), "pnts": pnts})
    except Exception as exc:
        return RawEEG(ok=False, fmt="SET", file_size_bytes=file_size, error=f"parse error: {exc}")


def _find_eeg_struct(value) -> Optional[dict]:
    if isinstance(value, dict) and value.get("__struct__"):
        recs = value.get("records") or []
        if recs:
            return recs[0]
    return None


def _channel_labels(chanlocs) -> list:
    if not (isinstance(chanlocs, dict) and chanlocs.get("__struct__")):
        return []
    out = []
    for rec in chanlocs.get("records", []):
        out.append(_as_text(rec.get("labels")) or f"CH{len(out) + 1}")
    return out


def _events_to_annotations(event, srate) -> list:
    if not (isinstance(event, dict) and event.get("__struct__")):
        return []
    out = []
    for rec in event.get("records", []):
        etype = _as_text(rec.get("type"))
        latency = _scalar(rec.get("latency"), 0.0)
        onset = round((latency - 1) / srate, 6) if srate else 0.0
        out.append({"onset_seconds": max(0.0, onset), "duration_seconds": 0.0,
                    "description": etype or "event"})
    return out
