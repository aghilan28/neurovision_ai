# Application Backend Platform — Design (Productization P6)

## Objective

Expose the internal P1–P5 platform as an **application backend**: a user can
authenticate, upload a real EEG file, trigger analysis, and retrieve a prediction +
confidence + explanation — through governed, in-process backend services. No frontend,
deployment, monitoring, or cloud infrastructure.

## Composition

`ApplicationBackendService` is the composition hub. It constructs the reused services
over a **single shared** `ml.lineage.LineageTracker` and the shared `ImmutableAuditLog`:

```
CaseService ─┐
EEGFoundationService (P1) ─┤
SignalProcessingService (P2) ─┤  shared LineageTracker + ImmutableAuditLog
FeatureEngineeringService (P3) ─┤
ModelFoundationService (P4) ─┤
InferenceFoundationService (P5)─┘
```

and adds the P6 subsystems: `UserService`, `AuthService`, `EegWorkflowService`,
`ApplicationAPI`, `BackendRegistry`, application storage, validators, and reports.

## Request lifecycle (API layer)

```
ApiRequest → mint request id → authenticate (if not public) →
RequestValidator (auth / authorization / request-structure / file-structure) →
dispatch to a reused domain operation → ApiResponse →
record RequestRecord + ResponseRecord (immutably audited + registered)
```

The API is **versioned** (`v1`) and in-process — there is no HTTP server or network
socket. Authorization is role-based over a closed `UserRole` set; `register`/`login`
are public, write operations (`upload`, `start_analysis`) require a write-capable role.

## EEG workflow (orchestration only)

`EegWorkflowService.run` executes the closed, ordered stage set
`UPLOAD → VALIDATE → PROCESS → FEATURES → PREDICT → CONFIDENCE → EXPLANATION` by
delegating to the reused services. The P5 `predict` call produces the prediction,
confidence, calibration, and explanation together; the last three stages are recorded as
completed sub-steps of that one governed call. The workflow **duplicates no business
logic**.

## Lineage — the required chain

The P1–P5 clinical chain is preserved intact (`… → EEG → Case → Patient`). P6 adds three
new node kinds — `user`, `session`, `upload` — plus a `workflow` **join** node that
parents both the upload node and the prediction node. One `verify_chain` from the
workflow node therefore reaches every required kind:

```
User → Upload → EEG → Processed → Feature → Model → Prediction
            (+ Case, Patient, Dataset, Training Run via the reused branches)
```

## Determinism & security

* Everything except authentication secrets is content-addressed and deterministic
  (no wall-clock, no randomness). Re-running reproduces the same `prediction_id` and
  workflow version.
* Authentication secrets (password salts, session tokens) come from an injectable
  entropy source — secure (`secrets`) by default, deterministic in tests. Secrets never
  enter a content hash: `UserRecord` carries no password/salt; `SessionRecord` stores
  only a token *fingerprint*; passwords are PBKDF2-HMAC-SHA256 salted hashes held in a
  private credential store, separate from every other store and from all reports.

## Registry & validation

`BackendRegistry` indexes every entity (users, sessions, uploads, requests, responses,
workflows, analyses, api) and **rejects orphan records** (each entry must reference an
audit head + a lineage node). `ApplicationIntegrityValidator` reuses
`ml.validation.ValidationReport` to produce the eight integrity checks over a finalized
workflow: authentication, session, workflow, api, registry, audit, lineage, version.

## Out of scope (forbidden in P6)

Frontend, React/Next.js, mobile apps, Docker/Kubernetes, cloud deployment, monitoring,
observability, CI/CD, Productization P7+, and Version 5.
