"""Deterministic, spec-compliant writers for EEG test fixtures (Productization P1).

These produce **genuine** files in each format (EDF / EDF+ / BDF / BDF+ / FIF / SET)
by writing the real byte layout of each specification. They exist so the test suite has
real fixtures to parse (round-trip: spec-compliant write -> real parse -> metadata
recovered). They are deterministic (fixed values; no wall-clock, no randomness).

This is test-support code (it writes files), kept out of the runtime package. The
runtime ``backend/eeg_foundation`` only ever *reads* files.
"""

from __future__ import annotations

import struct

# ----------------------------------------------------------------------------- EDF / BDF
_EDF_DIG_MIN, _EDF_DIG_MAX = -32768, 32767
_BDF_DIG_MIN, _BDF_DIG_MAX = -8388608, 8388607


def _fix(s: str, n: int) -> bytes:
    return s.encode("ascii", "ignore")[:n].ljust(n, b" ")


def _int24_le(v: int) -> bytes:
    v &= 0xFFFFFF
    return bytes((v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF))


def write_edf_family(path, *, bdf=False, plus=False, n_signal=2, sfreq=256,
                     record_duration=1.0, n_records=2, labels=None, annotations=None):
    """Write a valid EDF / EDF+ / BDF / BDF+ file."""
    labels = labels or [f"EEG {i + 1}" for i in range(n_signal)]
    annotations = annotations or []
    bps = 3 if bdf else 2
    dig_min, dig_max = (_BDF_DIG_MIN, _BDF_DIG_MAX) if bdf else (_EDF_DIG_MIN, _EDF_DIG_MAX)
    nsamp = int(round(sfreq * record_duration))

    chan_labels = list(labels)
    nsamp_list = [nsamp] * n_signal
    ann_nsamp = 0
    if plus:
        ann_label = "BDF Annotations" if bdf else "EDF Annotations"
        chan_labels.append(ann_label)
        ann_nsamp = 16                      # 16 samples * bps bytes for TAL text
        nsamp_list.append(ann_nsamp)
    ns = len(chan_labels)

    # --- main header (256 bytes) ---
    version = b"\xffBIOSEMI".ljust(8, b" ") if bdf else _fix("0", 8)
    if plus:
        reserved = _fix("BDF+C" if bdf else "EDF+C", 44)
    else:
        reserved = _fix("24BIT" if bdf else "", 44)
    head = b"".join([
        version, _fix("X X X NeuroVision-fixture", 80), _fix("Startdate 01-JAN-2000 X X X", 80),
        _fix("01.01.00", 8), _fix("00.00.00", 8), _fix(str(256 * (ns + 1)), 8),
        reserved, _fix(str(n_records), 8), _fix(_fmt_num(record_duration), 8), _fix(str(ns), 4),
    ])
    assert len(head) == 256, len(head)

    # --- signal headers (ns * 256) ---
    def col(values, width):
        return b"".join(_fix(str(v), width) for v in values)

    pdim = ["uV"] * n_signal + (["" ] if plus else [])
    sig = b"".join([
        col(chan_labels, 16),
        col(["AgAgCl"] * ns, 80),
        col(pdim, 8),
        col([-200] * n_signal + ([-1] if plus else []), 8),
        col([200] * n_signal + ([1] if plus else []), 8),
        col([dig_min] * ns, 8),
        col([dig_max] * ns, 8),
        col([""] * ns, 80),
        col(nsamp_list, 8),
        col([""] * ns, 32),
    ])
    assert len(sig) == ns * 256, len(sig)

    # --- data records ---
    body = bytearray()
    for r in range(n_records):
        for _i in range(n_signal):
            for s in range(nsamp):
                val = ((r * 7 + s) % 101) - 50          # deterministic ramp
                body += _int24_le(val) if bdf else struct.pack("<h", val)
        if plus:
            tals = f"+{_fmt_num(r * record_duration)}\x14\x14\x00"
            if r == 0:
                for onset, desc in annotations:
                    tals += f"+{_fmt_num(onset)}\x14{desc}\x14\x00"
            block = tals.encode("utf-8")[: ann_nsamp * bps].ljust(ann_nsamp * bps, b"\x00")
            body += block

    with open(path, "wb") as fh:
        fh.write(head + sig + bytes(body))
    return path


def _fmt_num(x) -> str:
    if float(x).is_integer():
        return str(int(x))
    return repr(float(x))


def write_edf(path, **kw):
    return write_edf_family(path, bdf=False, plus=False, **kw)


def write_edf_plus(path, **kw):
    kw.setdefault("annotations", [(0.5, "Seizure"), (1.25, "IIC")])
    return write_edf_family(path, bdf=False, plus=True, **kw)


def write_bdf(path, **kw):
    return write_edf_family(path, bdf=True, plus=False, **kw)


def write_bdf_plus(path, **kw):
    kw.setdefault("annotations", [(0.75, "ArtifactStart")])
    return write_edf_family(path, bdf=True, plus=True, **kw)


def write_corrupted_edf(path, **kw):
    """A valid EDF header whose data section is truncated (corruption)."""
    import os
    tmp = path + ".full"
    write_edf(tmp, **kw)
    with open(tmp, "rb") as fh:
        data = fh.read()
    os.remove(tmp)
    keep = 256 * 3 + (len(data) - 256 * 3) // 3       # header(s) + ~1/3 of data
    with open(path, "wb") as fh:
        fh.write(data[:keep])
    return path


def write_corrupted_bdf(path, **kw):
    """A BDF file with a corrupted record-duration field (header-level corruption)."""
    write_bdf(path, **kw)
    with open(path, "r+b") as fh:
        fh.seek(244)                                   # record-duration field
        fh.write(_fix("0", 8))                         # invalid (<= 0)
    return path


def write_unsupported(path):
    """A non-EEG file (unsupported format)."""
    with open(path, "wb") as fh:
        fh.write(b"RIFF\x00\x00\x00\x00WAVEfmt this is not an EEG file\n")
    return path


# ----------------------------------------------------------------------------- FIF
FIFF_FILE_ID, FIFF_NCHAN, FIFF_SFREQ = 100, 200, 201
FIFF_CH_INFO, FIFF_MEAS_DATE, FIFF_DATA_BUFFER = 203, 204, 300
_FIFFT_INT, _FIFFT_FLOAT, _FIFFT_ID_STRUCT, _FIFFT_CH_INFO_STRUCT = 3, 4, 31, 30


def _fif_tag(kind, dtype, data):
    return struct.pack(">iiii", kind, dtype, len(data), 0) + data


def write_fif(path, *, n_channels=3, sfreq=512.0, n_samples=512, meas_date=946684800):
    tags = [_fif_tag(FIFF_FILE_ID, _FIFFT_ID_STRUCT, struct.pack(">5i", 0, 0, 0, 0, 0))]
    tags.append(_fif_tag(FIFF_NCHAN, _FIFFT_INT, struct.pack(">i", n_channels)))
    tags.append(_fif_tag(FIFF_SFREQ, _FIFFT_FLOAT, struct.pack(">f", sfreq)))
    tags.append(_fif_tag(204, _FIFFT_INT, struct.pack(">ii", meas_date, 0)))   # FIFF_MEAS_DATE
    for i in range(n_channels):
        ci = bytearray(96)
        struct.pack_into(">i", ci, 0, i + 1)          # scanno
        struct.pack_into(">i", ci, 4, i + 1)          # logno
        struct.pack_into(">i", ci, 8, 2)              # kind = EEG
        name = f"EEG{i + 1:03d}".encode("ascii")[:16]
        ci[80:80 + len(name)] = name
        tags.append(_fif_tag(FIFF_CH_INFO, _FIFFT_CH_INFO_STRUCT, bytes(ci)))
    buf = struct.pack(">%df" % (n_channels * n_samples), *([0.0] * (n_channels * n_samples)))
    tags.append(_fif_tag(FIFF_DATA_BUFFER, _FIFFT_FLOAT, buf))
    with open(path, "wb") as fh:
        fh.write(b"".join(tags))
    return path


# ----------------------------------------------------------------------------- SET (MAT v5)
miINT8, miINT32, miUINT32, miDOUBLE, miMATRIX, miUTF8 = 1, 5, 6, 9, 14, 16
mxCHAR, mxDOUBLE, mxSTRUCT = 4, 6, 2


def _mat_el(dtype, payload: bytes) -> bytes:
    pad = (8 - (len(payload) % 8)) % 8
    return struct.pack("<II", dtype, len(payload)) + payload + (b"\x00" * pad)


def _array_flags(cls: int) -> bytes:
    return _mat_el(miUINT32, struct.pack("<II", cls, 0))


def _dims(*d) -> bytes:
    return _mat_el(miINT32, struct.pack("<%di" % len(d), *d))


def _name(s: str) -> bytes:
    return _mat_el(miINT8, s.encode("ascii"))


def _double_matrix(value: float, name: str = "") -> bytes:
    payload = _array_flags(mxDOUBLE) + _dims(1, 1) + _name(name) + \
        _mat_el(miDOUBLE, struct.pack("<d", float(value)))
    return _mat_el(miMATRIX, payload)


def _char_matrix(text: str, name: str = "") -> bytes:
    data = text.encode("utf-8")
    payload = _array_flags(mxCHAR) + _dims(1, len(text)) + _name(name) + _mat_el(miUTF8, data)
    return _mat_el(miMATRIX, payload)


def _struct_matrix(field_names, records, dims, name: str = "") -> bytes:
    """records: list (len == prod(dims)) of dict field->element-bytes (already miMATRIX)."""
    fnl = 32
    fn_bytes = b"".join(fn.encode("ascii")[:fnl].ljust(fnl, b"\x00") for fn in field_names)
    payload = _array_flags(mxSTRUCT) + _dims(*dims) + _name(name) + \
        _mat_el(miINT32, struct.pack("<i", fnl)) + _mat_el(miINT8, fn_bytes)
    for rec in records:
        for fn in field_names:
            payload += rec[fn]
    return _mat_el(miMATRIX, payload)


def write_set(path, *, n_channels=4, srate=250.0, pnts=500, setname="fixture",
              events=None):
    events = events if events is not None else [("Seizure", 100.0), ("IIC", 300.0)]
    labels = [f"Cz{i + 1}" for i in range(n_channels)]

    chan_records = [{"labels": _char_matrix(lbl)} for lbl in labels]
    chanlocs = _struct_matrix(["labels"], chan_records, dims=(1, n_channels))

    ev_records = [{"type": _char_matrix(t), "latency": _double_matrix(lat)}
                  for (t, lat) in events]
    event = _struct_matrix(["type", "latency"], ev_records, dims=(1, len(events))) if events \
        else _struct_matrix(["type", "latency"], [], dims=(0, 0))

    xmax = (pnts - 1) / srate
    fields = {
        "setname": _char_matrix(setname),
        "nbchan": _double_matrix(n_channels),
        "srate": _double_matrix(srate),
        "pnts": _double_matrix(pnts),
        "xmin": _double_matrix(0.0),
        "xmax": _double_matrix(xmax),
        "data": _mat_el(miMATRIX, _array_flags(mxDOUBLE) + _dims(0, 0) + _name("")
                        + _mat_el(miDOUBLE, b"")),
        "chanlocs": chanlocs,
        "event": event,
    }
    field_order = ["setname", "nbchan", "srate", "pnts", "xmin", "xmax", "data",
                   "chanlocs", "event"]
    eeg = _struct_matrix(field_order, [fields], dims=(1, 1), name="EEG")

    header = b"MATLAB 5.0 MAT-file, NeuroVision fixture".ljust(116, b" ")
    header += struct.pack("<q", 0)                    # subsys offset
    header += struct.pack("<H", 0x0100)               # version
    header += b"IM"                                    # little-endian indicator
    with open(path, "wb") as fh:
        fh.write(header + eeg)
    return path
