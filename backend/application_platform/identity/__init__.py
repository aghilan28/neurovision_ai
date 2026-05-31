"""Deterministic identity generation for the Application Platform (Track 3).

Content-addressed ``{kind}+{hash16}`` ids (the platform-wide scheme, NR-6), derived from
real content (upload fingerprint, backend ids, prediction signatures) — never from a
wall-clock or a counter — so identical inputs reproduce identical ids.
"""

from __future__ import annotations

from typing import Mapping

from ml.provenance import content_id  # allowed: backend -> ml

_KINDS = ("app_upload", "app_prediction_request", "app_prediction_result", "app_analysis",
          "app_report", "app_workflow", "app_readiness")


def mint(kind: str, payload: Mapping[str, object]) -> str:
    if kind not in _KINDS:
        raise ValueError(f"unknown identity kind {kind!r}")
    return content_id(kind, dict(payload))


__all__ = ["mint"]
