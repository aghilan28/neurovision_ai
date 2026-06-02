"""A tiny, byte-exact EDF/EDF+/BDF/BDF+ writer — *test scaffolding only*.

Generates small, deterministic, **real** EDF-family fixtures that MNE-Python reads
back faithfully (verified in the test suite). Not production code and not collected
by pytest (no ``test_`` prefix); the EEG Foundation never imports it.

EDF/BDF on-disk format: a 256-byte ASCII header + per-signal header arrays
(256 bytes each) + data records. EDF stores 16-bit little-endian samples; BDF
stores 24-bit little-endian samples. EDF+/BDF+ add an annotations channel carrying
time-stamped annotation lists (TALs).
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

_ANNOT_LABEL = {"EDF": "EDF Annotations", "BDF": "BDF Annotations"}


def _fld(value: object, width: int) -> bytes:
    """Left-justified, space-padded ASCII field of exactly ``width`` bytes."""
    b = str(value).encode("ascii")
    if len(b) > width:
        raise ValueError(f"field {value!r} exceeds {width} bytes")
    return b + b" " * (width - len(b))


def write_edf_like(
    path: str,
    *,
    fmt: str = "EDF",
    sfreq: int = 256,
    n_records: int = 2,
    record_duration: int = 1,
    labels: Sequence[str] = ("Fp1", "Fp2", "Cz"),
    annotations: Optional[Sequence[tuple[float, float, str]]] = None,
    patient_id: str = "X X X X",
    recording_id: str = "Startdate X X X X",
) -> str:
    """Write a small, valid EDF/EDF+/BDF/BDF+ file and return ``path``.

    ``fmt`` is one of ``EDF``, ``EDF+``, ``BDF``, ``BDF+``. Annotations (only for the
    ``+`` variants) are ``(onset_seconds, duration_seconds, description)`` tuples.
    """
    if fmt not in ("EDF", "EDF+", "BDF", "BDF+"):
        raise ValueError(f"unsupported fmt {fmt!r}")
    is_bdf = fmt.startswith("BDF")
    is_plus = fmt.endswith("+")
    family = "BDF" if is_bdf else "EDF"
    bps = 3 if is_bdf else 2
    nr = int(sfreq * record_duration)
    dmin, dmax = (-8388608, 8388607) if is_bdf else (-32768, 32767)
    n_data = len(labels)

    # --- deterministic data records (a simple per-channel sine ramp) ---
    data_records: list[bytes] = []
    for _r in range(n_records):
        rec = bytearray()
        for c in range(n_data):
            for i in range(nr):
                v = int(1000 * math.sin(2 * math.pi * (i / max(nr, 1)))) + c * 10
                v = max(dmin, min(dmax, v))
                rec += (v & ((1 << (8 * bps)) - 1)).to_bytes(bps, "little")
        data_records.append(bytes(rec))

    # --- EDF+/BDF+ annotation channel (TALs) ---
    annot_nr = 0
    annot_records: list[bytes] = []
    if is_plus:
        annot_nr = 32  # samples/record in the annotation channel (room for the TALs)
        pad = annot_nr * bps
        for r in range(n_records):
            tb = b"+%d\x14\x14\x00" % (r * record_duration)  # time-keeping TAL
            if r == 0 and annotations:
                for onset, dur, desc in annotations:
                    on = ("%g" % onset).encode("ascii")
                    d = (b"\x15" + ("%g" % dur).encode("ascii")) if dur else b""
                    tb += b"+" + on + d + b"\x14" + desc.encode("ascii") + b"\x14\x00"
            if len(tb) > pad:
                raise ValueError("annotation TAL too large for the annotation channel")
            annot_records.append(tb + b"\x00" * (pad - len(tb)))

    ns = n_data + (1 if is_plus else 0)
    header_bytes = 256 + ns * 256
    version = b"\xffBIOSEMI" if is_bdf else b"0       "
    reserved_map = {
        "EDF": b" " * 44, "EDF+": _fld("EDF+C", 44),
        "BDF": _fld("24BIT", 44), "BDF+": _fld("BDF+C", 44),
    }

    h = bytearray()
    h += version
    h += _fld(patient_id, 80)
    h += _fld(recording_id, 80)
    h += _fld("01.01.21", 8)        # start date dd.mm.yy
    h += _fld("00.00.00", 8)        # start time hh.mm.ss
    h += _fld(header_bytes, 8)
    h += reserved_map[fmt]
    h += _fld(n_records, 8)
    h += _fld(record_duration, 8)
    h += _fld(ns, 4)

    all_labels = list(labels) + ([_ANNOT_LABEL[family]] if is_plus else [])
    for i in range(ns):
        h += _fld(all_labels[i], 16)
    for _ in range(ns):
        h += _fld("", 80)                                    # transducer
    for i in range(ns):
        h += _fld("uV" if i < n_data else "", 8)             # physical dimension
    for i in range(ns):
        h += _fld(-200 if i < n_data else -1, 8)             # physical minimum
    for i in range(ns):
        h += _fld(200 if i < n_data else 1, 8)               # physical maximum
    for _ in range(ns):
        h += _fld(dmin, 8)                                   # digital minimum
    for _ in range(ns):
        h += _fld(dmax, 8)                                   # digital maximum
    for _ in range(ns):
        h += _fld("", 80)                                    # prefiltering
    for i in range(ns):
        h += _fld(nr if i < n_data else annot_nr, 8)         # samples per record
    for _ in range(ns):
        h += _fld("", 32)                                    # reserved
    assert len(h) == header_bytes, (len(h), header_bytes)

    with open(path, "wb") as fh:
        fh.write(bytes(h))
        for r in range(n_records):
            fh.write(data_records[r])
            if is_plus:
                fh.write(annot_records[r])
    return path
