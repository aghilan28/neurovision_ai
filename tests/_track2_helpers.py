"""Shared helpers for Track 2 (Real Model Training) tests.

Network-free real-data path: lays out the committed **real EDF fixtures** as a CHB-MIT
dataset (reusing the Track-1 helper) so the whole training pipeline runs on genuine EDF
bytes + real seizure annotations with no network. A real-corpus path is used when the
PhysioNet CHB-MIT subset has been acquired locally.
"""

from __future__ import annotations

from _track1_helpers import build_local_chb_mit, real_chb_mit_root  # noqa: F401 (re-export)

from backend.real_model_training import RealModelTrainingService


def develop_local(tmp_path, **kwargs):
    """Build a local CHB-MIT dataset under ``tmp_path`` and run the Track-2 program.

    Uses a tiny window so the 2-second fixtures yield several windows per recording with
    both classes present (the EDF+ fixture carries a real ``seizure_onset`` annotation).
    """
    build_local_chb_mit(str(tmp_path))
    svc = RealModelTrainingService(data_root=str(tmp_path))
    params = dict(window_seconds=0.5, stride_seconds=0.25, background_per_seizure=3)
    params.update(kwargs)
    outcome = svc.develop(allow_download=False, **params)
    return svc, outcome
