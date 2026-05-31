"""Shared helpers for Track 3 (Real Product Application) tests.

Provides a fast, real-data product fixture: a model prepared from bounded segments of the
committed **real EDF fixtures** (network-free) or the locally-acquired real CHB-MIT corpus
when present, plus the FastAPI app + TestClient driving the real HTTP surface.
"""

from __future__ import annotations

import os

from _track1_helpers import build_local_chb_mit, real_chb_mit_root  # noqa: F401 (re-export)

from backend.application_platform import ApplicationPlatformService, create_app
from backend.application_platform.uploads import prepare_bounded_segment
from backend.model_foundation import ModelArchitecture

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "eeg")


def _bounded(path: str, seconds: float) -> str:
    with open(path, "rb") as fh:
        content = fh.read()
    seg, _fp, _sz = prepare_bounded_segment(content, os.path.basename(path),
                                            analysis_seconds=seconds)
    return seg


def make_product(*, analysis_seconds: float = 2.0,
                 architecture=ModelArchitecture.EEGNET):
    """Return an ``ApplicationPlatformService`` with a model prepared from real EEG.

    Uses the committed real EDF fixtures (``valid.edf`` + ``valid_edf_plus.edf``) as a tiny
    real cohort so model preparation + analysis are fast and network-free. A small
    ``analysis_seconds`` keeps the bounded segment within the 2-second fixtures.
    """
    svc = ApplicationPlatformService(analysis_seconds=analysis_seconds)
    cohort = [("p-a", "c-a", os.path.join(FIXTURE_DIR, "valid.edf")),
              ("p-b", "c-b", os.path.join(FIXTURE_DIR, "valid_edf_plus.edf"))]
    svc.prepare_model(cohort, architecture=architecture)
    return svc


def make_client(svc: ApplicationPlatformService):
    from fastapi.testclient import TestClient

    return TestClient(create_app(svc))


def real_eeg_bytes() -> bytes:
    """Bytes of a committed real EDF fixture (a genuine EDF file, network-free)."""
    with open(os.path.join(FIXTURE_DIR, "valid_edf_plus.edf"), "rb") as fh:
        return fh.read()
