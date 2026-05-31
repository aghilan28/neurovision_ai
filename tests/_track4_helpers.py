"""Shared helpers for Track 4 (Operational Readiness & Deployment Qualification) tests.

Builds a real Track-3 product (model prepared from the committed real EDF fixtures, a real
EEG analysed through the real workflow), then a Track-4 ``OperationsPlatformService`` that
qualifies it — network-free. A real-corpus path is used when the PhysioNet CHB-MIT subset is
present locally.
"""

from __future__ import annotations

import base64

from _track3_helpers import make_client, make_product, real_chb_mit_root, real_eeg_bytes  # noqa: F401

from backend.operations_platform import OperationsPlatformService


def make_qualified_product(*, analysis_seconds: float = 2.0, run_workflow: bool = True):
    """Return a real Track-3 product with (optionally) one completed real workflow."""
    product = make_product(analysis_seconds=analysis_seconds)
    if run_workflow:
        client = make_client(product)
        client.post("/v1/auth/register", json={"username": "u", "password": "pw-123456"})
        tok = client.post("/v1/auth/login",
                          json={"username": "u", "password": "pw-123456"}).json()["token"]
        client.post("/v1/uploads",
                    json={"filename": "v.edf",
                          "content_base64": base64.b64encode(real_eeg_bytes()).decode()},
                    headers={"Authorization": f"Bearer {tok}"})
    return product


def make_operations(*, analysis_seconds: float = 2.0, run_workflow: bool = True):
    """Return ``(product, OperationsPlatformService)`` ready to ``qualify()``."""
    product = make_qualified_product(analysis_seconds=analysis_seconds, run_workflow=run_workflow)
    return product, OperationsPlatformService(product)
