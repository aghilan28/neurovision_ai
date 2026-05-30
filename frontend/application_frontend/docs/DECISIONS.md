# Application Frontend Platform — Key Decisions (Productization P7)

See `.gcc/decisions/ADR-0020-productization-p7-application-frontend.md` for the full ADR.

1. **Presentation-only, stdlib-only (NR-8).** The frontend imports no domain module. It
   is the same boundary every prior NeuroVision frontend upholds; `test_boundaries.py`
   enforces it.

2. **Gateway port + scripts-seam adapter.** The frontend consumes the backend through an
   abstract `BackendGateway` (dict in / dict out matching the real `v1` API). The concrete
   `LiveBackendGateway` that calls `ApplicationAPI` lives in `scripts/` (the only place
   allowed to import both layers). This is how the frontend "consumes actual backend
   contracts" and "backend integration works" without code coupling — and tests/verify use
   the **real** backend (no fake contracts).

3. **No business logic, no bypass.** Controllers only validate fields for UX, call the
   gateway, and shape results. There is no auth/workflow/inference logic in the frontend;
   it never bypasses a backend service.

4. **Deterministic static HTML, no JavaScript.** Pages render byte-identically from state
   (inline CSS, inline content, all escaped) — consistent with the platform's other
   frontends and with NR-9/NR-10 determinism.

5. **Secrets never enter the frontend state/render.** The raw session token is volatile
   (used only as the gateway bearer) and is never serialized or rendered; the state
   snapshot is secret-free.

6. **Faithful uncertainty (NR-4).** The prediction view always shows confidence +
   calibration alongside the label.

## Honest limitations (recorded, not hidden — NR-2)

* The backend P6 API exposes no "current user" endpoint, so the dashboard user summary
  shows what login returned (username, user id, session). Not a gap to fix in P7 (it would
  require modifying a prior phase).
* `LIST_REPORTS` returns the backend's `analysis_reports` set (prediction / confidence /
  calibration / explainability / analysis / workflow / lineage / inference). The
  "validation" and "audit" report *categories* in the directive are surfaced from fields
  embedded in those reports (chain-verified, audit-verified, event counts) rather than as
  separate documents — staying within P7 (no backend change).
* The analysis summary omits the ordered stage list; the frontend enriches it from the
  workflow report so the progress view is faithful.
