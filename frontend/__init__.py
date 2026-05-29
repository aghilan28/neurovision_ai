"""``frontend/`` — Presentation Layer.

The clinician/researcher-facing layer. Its hard constraint is the platform's
strictest boundary: **the frontend imports no domain module** (not ``ml``,
``evaluation``, ``datasets``, ``preprocessing``, nor even ``backend`` as code).

V1 scope: the **offline research application** (``frontend.offline_research_app``)
— a presentation-only workstation that reads the backend's *registered artifact
JSON files* and renders them (view-models + a static, offline HTML report). In the
offline setting the frontend↔backend boundary is realized as a **data/file
boundary** (read registered artifacts), which is even stricter than the V2 API
boundary: zero code coupling (NR-8). Recorded in ``.gcc/decisions/ADR-0002``.

Imports: Python standard library only.
"""
