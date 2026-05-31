"""Deterministic identity generation for the Operations Platform (Track 4).

Content-addressed ``{kind}+{hash16}`` ids (the platform-wide scheme, NR-6), derived from the
observed product state (health signatures, metric counts, diagnostic/qualification
signatures) — never from a wall-clock or a counter — so identical observed state reproduces
identical ids.
"""

from __future__ import annotations

from typing import Mapping

from ml.provenance import content_id  # allowed: backend -> ml

_KINDS = ("ops_health_check", "ops_metrics_snapshot", "ops_diagnostic", "ops_qualification",
          "ops_readiness")


def mint(kind: str, payload: Mapping[str, object]) -> str:
    if kind not in _KINDS:
        raise ValueError(f"unknown identity kind {kind!r}")
    return content_id(kind, dict(payload))


__all__ = ["mint"]
