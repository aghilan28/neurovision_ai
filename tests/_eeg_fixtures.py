"""Deterministic EEG fixture generator — *test scaffolding only*.

Produces the small, real fixture files the EEG Foundation suite reads:

  valid.edf · valid_edf_plus.edf · valid.bdf · valid_bdf_plus.bdf ·
  valid_raw.fif · valid.set · corrupted.edf · corrupted.bdf · unsupported.eeg

EDF-family files are written by the byte-exact ``_eeg_edf_writer`` (MNE reads them
back); FIF via MNE's native writer; SET via a minimal EEGLAB (MATLAB v5) container
written with scipy. The committed files live in ``tests/fixtures/eeg/``; this module
can regenerate any that are missing. Not collected by pytest (no ``test_`` prefix).
"""

from __future__ import annotations

import os
import warnings

from _eeg_edf_writer import write_edf_like

# Canonical fixture filenames (the committed set under tests/fixtures/eeg/).
VALID_EDF = "valid.edf"
VALID_EDF_PLUS = "valid_edf_plus.edf"
VALID_BDF = "valid.bdf"
VALID_BDF_PLUS = "valid_bdf_plus.bdf"
VALID_FIF = "valid_raw.fif"        # MNE requires a *_raw.fif / *-raw.fif suffix
VALID_SET = "valid.set"
CORRUPTED_EDF = "corrupted.edf"
CORRUPTED_BDF = "corrupted.bdf"
UNSUPPORTED = "unsupported.eeg"

ALL_FIXTURES = (
    VALID_EDF, VALID_EDF_PLUS, VALID_BDF, VALID_BDF_PLUS, VALID_FIF, VALID_SET,
    CORRUPTED_EDF, CORRUPTED_BDF, UNSUPPORTED,
)

_SFREQ = 256
_LABELS = ("Fp1", "Fp2", "Cz")
_ANNOT = [(0.5, 0.0, "seizure_onset"), (1.25, 0.5, "artifact")]


def _write_fif(path: str) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import numpy as np
        import mne

        mne.set_log_level("ERROR")
        n = _SFREQ * 2
        data = 1e-6 * np.sin(2 * np.pi * np.outer([1.0, 2.0, 3.0], np.arange(n)) / _SFREQ)
        info = mne.create_info(ch_names=list(_LABELS), sfreq=float(_SFREQ), ch_types="eeg")
        raw = mne.io.RawArray(np.ascontiguousarray(data), info, verbose="ERROR")
        raw.set_meas_date(0)  # deterministic epoch (no wall-clock)
        raw.set_annotations(mne.Annotations(
            onset=[a[0] for a in _ANNOT], duration=[a[1] for a in _ANNOT],
            description=[a[2] for a in _ANNOT]))
        raw.save(path, overwrite=True, verbose="ERROR")


def _write_set(path: str) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import numpy as np
        from scipy.io import savemat

        n = _SFREQ * 2
        arr = np.ascontiguousarray(
            np.sin(2 * np.pi * np.outer([1.0, 2.0, 3.0], np.arange(n)) / _SFREQ)).astype(np.float32)
        chanlocs = np.zeros((1, len(_LABELS)), dtype=[("labels", "O")])
        for i, lab in enumerate(_LABELS):
            chanlocs["labels"][0, i] = lab
        events = np.zeros((1, len(_ANNOT)), dtype=[("type", "O"), ("latency", "O"), ("duration", "O")])
        for i, (onset, dur, desc) in enumerate(_ANNOT):
            events["type"][0, i] = desc
            events["latency"][0, i] = onset * _SFREQ + 1  # EEGLAB latency is 1-based samples
            events["duration"][0, i] = dur * _SFREQ
        eeg = dict(
            setname="nv_fixture", nbchan=float(len(_LABELS)), trials=1.0, pnts=float(n),
            srate=float(_SFREQ), xmin=0.0, xmax=(n - 1) / _SFREQ, data=arr,
            icawinv=[], icasphere=[], icaweights=[], chanlocs=chanlocs, event=events,
            ref="common", times=np.arange(n) / _SFREQ)
        savemat(path, {"EEG": eeg}, appendmat=False)
        # scipy.io.savemat writes a wall-clock timestamp into the MATLAB v5 header.
        # The fixture content is deterministic, so normalize that informational header.
        fixed_header = b"MATLAB 5.0 MAT-file, NeuroVision deterministic EEGLAB fixture"
        with open(path, "r+b") as fh:
            fh.write(fixed_header.ljust(116, b" "))


def _corrupt_ns_field(src_path: str, dest_path: str) -> None:
    """Copy an EDF/BDF file but corrupt the 'number of signals' header field.

    The format magic stays intact (so detection still classifies it), but the
    header is no longer decodable -> a CRITICAL ``corrupted_file`` finding.
    """
    with open(src_path, "rb") as fh:
        data = bytearray(fh.read())
    data[252:256] = b"ABCD"  # ns field (offset 252..256) -> non-numeric
    with open(dest_path, "wb") as fh:
        fh.write(bytes(data))


def generate_fixtures(dest_dir: str, *, force: bool = False) -> dict:
    """Create all fixtures under ``dest_dir`` (skipping existing unless ``force``)."""
    os.makedirs(dest_dir, exist_ok=True)
    paths = {name: os.path.join(dest_dir, name) for name in ALL_FIXTURES}

    def _missing(name: str) -> bool:
        return force or not os.path.exists(paths[name])

    if _missing(VALID_EDF):
        write_edf_like(paths[VALID_EDF], fmt="EDF", sfreq=_SFREQ, labels=_LABELS)
    if _missing(VALID_EDF_PLUS):
        write_edf_like(paths[VALID_EDF_PLUS], fmt="EDF+", sfreq=_SFREQ, labels=_LABELS, annotations=_ANNOT)
    if _missing(VALID_BDF):
        write_edf_like(paths[VALID_BDF], fmt="BDF", sfreq=_SFREQ, labels=_LABELS)
    if _missing(VALID_BDF_PLUS):
        write_edf_like(paths[VALID_BDF_PLUS], fmt="BDF+", sfreq=_SFREQ, labels=_LABELS, annotations=_ANNOT)
    if _missing(VALID_FIF):
        _write_fif(paths[VALID_FIF])
    if _missing(VALID_SET):
        _write_set(paths[VALID_SET])

    # corrupted variants are derived from freshly-written valid headers
    if _missing(CORRUPTED_EDF):
        tmp = os.path.join(dest_dir, "_tmp_corrupt.edf")
        write_edf_like(tmp, fmt="EDF", sfreq=_SFREQ, labels=_LABELS)
        _corrupt_ns_field(tmp, paths[CORRUPTED_EDF])
        os.remove(tmp)
    if _missing(CORRUPTED_BDF):
        tmp = os.path.join(dest_dir, "_tmp_corrupt.bdf")
        write_edf_like(tmp, fmt="BDF", sfreq=_SFREQ, labels=_LABELS)
        _corrupt_ns_field(tmp, paths[CORRUPTED_BDF])
        os.remove(tmp)
    if _missing(UNSUPPORTED):
        with open(paths[UNSUPPORTED], "wb") as fh:
            fh.write(b"NOT-AN-EEG-FILE\nthis is plain text, not a supported EEG container.\n" * 4)

    return paths
