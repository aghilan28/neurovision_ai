# Real Product Application — Decisions (Track 3)

Canonical record: [`ADR-0032`](../../../.gcc/decisions/ADR-0032-track3-real-product-application.md).

- **New sibling subsystem, real FastAPI HTTP API.** The directive requires FastAPI; it is an
  external package, so importing it under `backend/` does not break the internal-import
  boundary test. The API is a thin typed/versioned (`/v1`) dispatcher with no business logic.
- **Reuse `application_backend` (no duplicate workflow logic).** It already runs the reused
  P1-P5 upload → prediction workflow; Track 3 wraps it and adds the product layer (bounded
  upload, prediction/evidence projection, JSON/HTML/PDF reports, registry, readiness, lineage).
- **Bounded analysis segment.** Real recordings are hours long; the product analyses a
  deterministic leading segment (default 20 s) for interactivity. Full upload preserved.
- **JSON/HTML/PDF, stdlib-only + deterministic.** Canonical JSON, escaped static HTML, and a
  minimal valid PDF writer — no `reportlab`/`weasyprint` dependency.
- **`READY_FOR_USERS`** readiness; shared `ml.lineage` + `ImmutableAuditLog`; chain
  Dataset → Recording → Model → Prediction Request → Prediction Result → Report.
- **Fixed a real P2 bug** (`signal_processing.detect_movement`: `float()` with 3 args) that
  only triggers on real long recordings and blocked the real-data workflow; `signal_processing`
  is not in Track 3's forbidden list. Prior P2 tests remain green.
- **Scope (NR-13).** No retraining / dataset / Track-1 / Track-2 / persistence / security /
  deployment changes.
- **Honesty (NR-2).** A working end-to-end product on real data + real models; the bounded
  segment is disclosed; predictions are evidence of a working product, not a clinical claim;
  production hosting/TLS/scaling are deployment concerns (out of scope).
