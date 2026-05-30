# Application Backend Platform — Key Decisions (Productization P6)

See `.gcc/decisions/ADR-0019-productization-p6-application-backend.md` for the full ADR.

1. **Reuse, never re-implement.** The hub orchestrates the existing P1–P5 services over
   one shared lineage tracker + audit log. No parallel EEG pipeline, model, audit, or
   lineage system is created.

2. **In-process API, not a server.** P6's scope is *backend access*, not serving. The
   API is a versioned (`v1`), structured, in-process request/response contract layer.
   FastAPI/HTTP/WebSockets/networking are explicitly out of scope (those belong to a
   later phase).

3. **A workflow join node realizes the required chain.** Rather than modifying the
   P1–P5 lineage (which would violate "do not redesign prior phases"), the workflow node
   parents both the upload node and the prediction node. A single `verify_chain` then
   spans `User → Upload → … → Prediction` while the clinical chain stays intact.

4. **Secrets are the only non-deterministic input, and they are quarantined.** Password
   salts and session tokens come from an injectable entropy source (secure by default,
   deterministic in tests). They never enter a content hash, a record, a report, or the
   lineage/audit trail. `UserRecord` carries no secret material; `SessionRecord` stores
   only a token fingerprint. This preserves platform determinism (NR-9/NR-10) and the
   reproducibility of every id/version/report, while keeping secure defaults.

5. **Local authentication only.** No social login, no OAuth providers — per the
   directive. PBKDF2-HMAC-SHA256 with a per-user salt; constant-time verification.

6. **No orphan records.** The registry rejects any entry without both an audit head and
   a lineage node, so every tracked entity is traceable and auditable.

7. **Model preparation is explicit.** `prepare_model` builds a patient-disjoint cohort
   by running the real P1–P3 pipeline over EEG files, then trains + registers a model
   via P4. Analysis predictions reuse that registered model via P5's deterministic
   reconstruction. The application serves predictions; it does not invent a parallel
   training path.

## Inherited platform gaps (unchanged, disclosed)

* **G3 — in-memory persistence.** Application storage is in-memory (plus a small
  content-addressed on-disk byte store for uploaded files), matching the platform's
  existing model. Durable databases remain out of scope.
* **G1 / G2** (synthetic-data lineage, unmechanized `.gcc` governance) are inherited and
  unchanged by P6.
