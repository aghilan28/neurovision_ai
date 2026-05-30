"""Schemas, determinism primitives, and event models for V2-P5.

This package is the single source of truth for:

* :mod:`~backend.multi_case_intelligence.schemas.determinism` — canonical
  serialization, content hashing, deterministic IDs and float quantization.
  These pure utilities are *also* reused by the V2-P6 decision-support subsystem
  so that both layers share one deterministic identity mechanism.
* :mod:`~backend.multi_case_intelligence.schemas.base` — immutable versioned
  artifact base types and references.
* :mod:`~backend.multi_case_intelligence.schemas.source` — the immutable source
  artifact contracts (Patient/Case/Review/Finding/Interpretation/Knowledge/
  Evidence) representing Version 2 clinical truth.
* :mod:`~backend.multi_case_intelligence.schemas.intelligence` — intelligence
  artifact types (cohorts, analytics, trends, quality reports, reports).
* :mod:`~backend.multi_case_intelligence.schemas.events` — immutable audit
  events and lineage records.
"""
