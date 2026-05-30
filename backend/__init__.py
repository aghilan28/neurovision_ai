"""NeuroVision AI — Application Layer (`backend/`).

This package is the Application Layer of the platform (see
``docs/architecture/LAYERED_ARCHITECTURE.md``). It orchestrates domain logic and
preserves uncertainty + provenance end-to-end.

Version 2 subsystems implemented here:

* ``multi_case_intelligence`` — V2-P5, Multi-Case Intelligence Layer.
* ``decision_support``        — V2-P6, Decision Support Layer.

Both subsystems are decision-support only. They never diagnose, treat, or make
autonomous clinical decisions, and they never mutate source clinical artifacts.
"""
