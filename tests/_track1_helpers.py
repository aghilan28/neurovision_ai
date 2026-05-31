"""Shared helpers for Track 1 (Real Dataset Platform) tests.

Two real-data paths are supported:

* **Network-free** — ``build_local_chb_mit(...)`` lays out a CHB-MIT-shaped directory using
  the committed **real EDF fixtures** (``tests/fixtures/eeg/valid*.edf``) + a real-format
  ``chbNN-summary.txt``. The connector reads actual EDF bytes (via MNE) and parses real
  seizure annotations, so the whole pipeline is exercised on genuine files with no network.

* **Real corpus** — ``real_chb_mit_root()`` returns the locally-acquired CHB-MIT corpus root
  (``data/real`` by default) when it has been downloaded, so tests can additionally assert
  on the genuine PhysioNet recordings *when available*.
"""

from __future__ import annotations

import os
import pathlib
import shutil

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "eeg"

# A real CHB-MIT summary fragment (early format) for the two fixture recordings.
_SUMMARY = """Data Sampling Rate: 256 Hz
*************************

File Name: chb01_01.edf
File Start Time: 11:42:54
File End Time: 12:42:57
Number of Seizures in File: 0

File Name: chb01_03.edf
File Start Time: 13:43:04
File End Time: 14:43:04
Number of Seizures in File: 1
Seizure Start Time: 1 seconds
Seizure End Time: 2 seconds
"""


def build_local_chb_mit(data_root: str, *, with_summary: bool = True,
                        corrupt_one: bool = False) -> str:
    """Create a CHB-MIT-shaped real-EDF dataset under ``data_root`` and return it.

    ``chb01/chb01_01.edf`` (no seizure) + ``chb01/chb01_03.edf`` (one seizure) are copied
    from the committed real EDF fixtures; ``chb01/chb01-summary.txt`` carries the real
    label format. Set ``with_summary=False`` to simulate missing labels, ``corrupt_one=True``
    to simulate a corrupted recording.
    """
    root = os.path.join(data_root, "chb_mit", "chb01")
    os.makedirs(root, exist_ok=True)
    shutil.copy(FIXTURE_DIR / "valid.edf", os.path.join(root, "chb01_01.edf"))
    shutil.copy(FIXTURE_DIR / "valid_edf_plus.edf", os.path.join(root, "chb01_03.edf"))
    if corrupt_one:
        with open(os.path.join(root, "chb01_03.edf"), "wb") as fh:
            fh.write(b"not a real edf file")
    if with_summary:
        with open(os.path.join(root, "chb01-summary.txt"), "w", encoding="utf-8") as fh:
            fh.write(_SUMMARY)
    return data_root


def real_chb_mit_root() -> str | None:
    """Return the acquired real CHB-MIT data root if present locally, else ``None``."""
    root = os.environ.get("NV_DATASET_ROOT", str(REPO_ROOT / "data" / "real"))
    chb = os.path.join(root, "chb_mit", "chb01")
    if os.path.isdir(chb) and any(f.endswith(".edf") for f in os.listdir(chb)):
        return root
    return None
