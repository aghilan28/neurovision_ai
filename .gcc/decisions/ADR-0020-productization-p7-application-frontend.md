# ADR-0020 — Productization P7: Application Frontend Platform

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P7
> **Builds on:** ADR-0001 … ADR-0019 (esp. P6 ADR-0019 — Application Backend)
> **Enforces / honors:** AP-4/NR-4 (faithful uncertainty), AP-7/NR-8 (boundaries — the
> strictest one), AP-6/NR-9/NR-10 (determinism), AP-9/NR-5 (this record), NR-6 (reuse),
> NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P7 **Application Frontend Platform**
(`frontend/application_frontend`) is shaped as it is, so the rationale survives turnover
(NR-14).

---

## 1. Context

P6 exposed the platform through an in-process application backend (`ApplicationAPI`,
`v1`). P7 turns that into a **usable product**: a real frontend through which a user can
log in, upload an EEG, run an analysis, and receive + review a prediction (confidence,
explanation) and its reports. The scope is **user interaction and nothing else** — no
deployment, monitoring, or cloud infrastructure.

The repository's strictest architectural rule (`tests/test_boundaries.py`) is
`ALLOWED["frontend"] = set()`: the frontend imports **no** domain module — not even
`backend` as code. Every prior NeuroVision frontend is therefore presentation-only Python.
P7 must be interactive *and* honour that rule.

## 2. Decisions

### D1 — Presentation-only, stdlib-only (NR-8)
`frontend/application_frontend` imports no domain module. It is standard-library only and
contains **no business logic**. The architecture-boundary tests stay green.

### D2 — Gateway port + scripts-seam adapter (consume real contracts, no coupling)
The frontend defines an abstract **`BackendGateway`** port — a single
`handle(operation, params, token) -> dict` exchanging plain dicts that mirror the
backend's *actual* `v1` API (the closed `ApiOperation` vocabulary, `ApiRequest` params,
`ApiResponse` body/status). The concrete **`LiveBackendGateway`** that drives the real
`ApplicationAPI` lives at the `scripts/` seam (`scripts.application_frontend_gateway`),
the only place allowed to import both layers. Tests, the verification script, and the
snapshot builder wire the **real** backend through this adapter — so the frontend is
exercised against actual contracts, never fakes. This realizes the canonical
frontend↔backend boundary: API-only, no code coupling.

### D3 — No bypass, no duplicated logic
Every action is a backend API call. Controllers only validate fields for UX, call the
gateway, and shape an `ActionResult`. There is no auth/workflow/inference logic in the
frontend, and no backend service is bypassed. The analysis UI **reflects** backend
workflow stages (it does not recreate the workflow engine).

### D4 — Deterministic static HTML, no JavaScript
Pages render byte-identically from state (inline CSS, escaped values, no JS, no external
assets) — consistent with the platform's other frontends and with NR-9/NR-10.

### D5 — Secrets never enter the frontend
The raw session token is volatile (used only as the gateway bearer) and is never
serialized or rendered. The state snapshot is secret-free and deterministic.

### D6 — Faithful uncertainty (NR-4)
The prediction view always shows confidence level + score + calibration alongside the
label; uncertainty is never flattened.

### D7 — Session-expiration handling is central and unambiguous
An `unauthorized` response to a *protected* action clears auth state and routes to login;
a failed *login* is treated as bad credentials, not expiration.

## 3. Consequences

- The deliverable executes end to end through a real frontend: log in → upload EEG → run
  analysis → receive prediction → view confidence → view explanation → access reports.
- `python -m scripts.verify_productization_p7` exercises all 15 criteria (**ALL PASS**),
  including all 12 backend operations exercised and the NR-8 boundary asserted.
- The new suites add 21 tests; the full repository suite is **790 passed** (was 769).
  `ruff` is clean on all new code; `tests/test_boundaries.py` stays green.
- No new runtime dependencies; the frontend is stdlib-only.

## 4. Scope guard (explicitly NOT built — NR-13)

Docker, Kubernetes, cloud deployment, monitoring, observability, CI/CD, Productization
P8+, and Version 5. No business logic in the frontend; no bypassing backend services.

## 5. Honest limitations / follow-ups (NR-2)

- The P6 API has no "current user" endpoint, so the dashboard user summary shows what
  login returned. Enriching it would require changing a prior phase (out of scope here).
- `LIST_REPORTS` returns the backend `analysis_reports` set; the directive's "validation"
  and "audit" report categories are surfaced from fields embedded in those reports rather
  than as separate documents (no backend change in P7).
- A real HTTP transport / browser SPA over the same gateway contract, plus deployment, are
  deliberately deferred to a later phase.
