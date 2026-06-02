"""``backend/`` — Application Layer.

Orchestrates the domain modules (``ml``, ``evaluation``, ``datasets``,
``preprocessing``) into application use cases while **preserving uncertainty and
provenance** end to end (AP-4/AP-5, NR-4/NR-11).

V1 scope: the **offline inference platform** (``backend.offline_inference``) — a
deterministic, offline, single-process orchestration of every V1 subsystem. No
APIs, no networking, no multi-user, no clinical deployment (those are V2+, see
``.gcc/decisions/ADR-0002``).

Boundary (NR-8): backend may import ``ml``/``evaluation``/``datasets``/
``preprocessing``; it must **never** import ``frontend``.
"""
