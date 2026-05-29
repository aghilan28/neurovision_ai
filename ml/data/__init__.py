"""``ml/data`` — the ML dataset adapter (the directive's ``ml/datasets``).

Bridges the platform's ``datasets`` module (patient-indexed, leakage-safe) and the
deterministic ``preprocessing`` transforms into model-ready arrays and typed
``InputBatch`` contracts. Named ``ml/data`` (not ``ml/datasets``) purely to avoid
shadowing the top-level ``datasets`` package; this naming choice is recorded in the
governance ADR.

Boundary: imports ``datasets`` and ``preprocessing`` only (allowed: ml -> both).
"""

from __future__ import annotations

from .adapter import PreparedData, prepare_split

__all__ = ["PreparedData", "prepare_split"]
