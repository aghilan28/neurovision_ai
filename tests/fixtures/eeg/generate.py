"""Generate the deterministic EEG test fixtures (Productization P1).

Writes genuine, spec-compliant files (EDF / EDF+ / BDF / BDF+ / FIF / SET) plus
corrupted and unsupported fixtures into this directory. Deterministic: re-running
produces byte-identical files. Run with ``python -m tests.fixtures.eeg.generate`` or
import ``generate_all``.
"""

from __future__ import annotations

import os

from _writers import (  # type: ignore  (same-dir import; see __main__/sys.path)
    write_edf, write_edf_plus, write_bdf, write_bdf_plus, write_fif, write_set,
    write_corrupted_edf, write_corrupted_bdf, write_unsupported,
)

FILES = {
    "valid.edf": lambda p: write_edf(p),
    "valid_plus.edf": lambda p: write_edf_plus(p),
    "valid.bdf": lambda p: write_bdf(p),
    "valid_plus.bdf": lambda p: write_bdf_plus(p),
    "valid.fif": lambda p: write_fif(p),
    "valid.set": lambda p: write_set(p),
    "corrupted.edf": lambda p: write_corrupted_edf(p),
    "corrupted.bdf": lambda p: write_corrupted_bdf(p),
    "unsupported.dat": lambda p: write_unsupported(p),
}


def generate_all(dest_dir: str | None = None) -> dict:
    dest_dir = dest_dir or os.path.dirname(os.path.abspath(__file__))
    os.makedirs(dest_dir, exist_ok=True)
    out = {}
    for name, fn in FILES.items():
        path = os.path.join(dest_dir, name)
        fn(path)
        out[name] = path
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    written = generate_all()
    for name, path in sorted(written.items()):
        print(f"{name:18s} {os.path.getsize(path):>8d} bytes")
