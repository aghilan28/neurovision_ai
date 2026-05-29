# ADR-0002 — V1-P7 Offline Inference Platform + V1-P8 Offline Research Application

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V1-P7 + V1-P8 (+ V1 Certification)
> **Builds on:** [ADR-0001](./ADR-0001-v1-p5-p6-baseline-models-and-uncertainty.md)
> **Enforces / honors:** AP-1 (no re-layering), AP-4/NR-4 (uncertainty), AP-5/AP-8/NR-11
> (traceability/audit), AP-6/NR-9/NR-10 (determinism/reproducibility), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), NR-12 (version gate), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the offline inference platform (`backend/offline_inference`) and the
offline research application (`frontend/offline_research_app`) are shaped as they
are, so the rationale survives turnover (NR-14).

---

## 1. Context

The V1-P7/P8 directive requires introducing the **Application** (`backend/`) and
**Presentation** (`frontend/`) layers as an **offline** inference platform and an
offline research workstation. The architecture docs (`LAYERED_ARCHITECTURE.md`,
the module READMEs) mark backend/frontend as **"introduced/owned from V2."** This
is therefore a deliberate, **governed scope extension**: introducing *offline-only*
forms of these layers in V1, with no V2 capabilities.

## 2. Decisions

### D1 — Offline-only backend/frontend; no V2 capabilities
We implement `backend/offline_inference` and `frontend/offline_research_app` as
**single-process, offline, deterministic** subsystems. We implement **no** APIs,
networking, real-time/streaming, multi-user, FHIR/EMR, alerting, or clinical
deployment (the directive's forbidden list, NR-13). The seven-layer architecture
is **populated, not re-layered** (AP-1).

### D2 — `frontend` imports **no** domain module (strictest boundary)
The import rules forbid the frontend from importing any domain module — including
`backend` as code (the API-only rule, NR-8). In the offline setting there is no
network API, so we realize the frontend↔backend boundary as a **data/file
boundary**: the backend writes **registered artifact JSON**; the frontend reads
those files (stdlib only) and renders them. This is *stricter* than the V2 API
boundary (zero code coupling) and is enforced by `tests/test_boundaries.py`
(`frontend` imports nothing internal; `backend ↛ frontend`).

Consequence: "UI is presentation only / everything displayed originates from
registered artifacts" (directive) is satisfied structurally — the UI **cannot**
recompute domain values because it cannot import domain code.

### D3 — `backend` orchestrates; it does not re-implement
`backend/offline_inference` imports `ml`, `evaluation`, `datasets`,
`preprocessing` and **composes** them (NR-6: no re-implementation). The
`EvaluationPort` inversion from ADR-0001 still holds: the orchestrator (in
`backend`, above both `ml` and `evaluation`) wires model outputs through the
evaluation framework; `ml` still never imports `evaluation`.

### D4 — Determinism: content-addressed ids, timing is non-hashed
`inference_id`, lineage ids, and the execution **content signature** are hashes of
canonical content and **exclude wall-clock timing**. Execution timing/durations
are recorded as **non-hashed** metadata (`RealClock`/`FakeClock`). Weights/artifacts
use the deterministic serialization from ADR-0001. Result: identical config →
identical `inference_id`, identical artifact checksums, identical rendered HTML.

### D5 — Minimal `datasets` intelligence surface (V1-P3)
The application's dataset workflow and the orchestrator's Dataset-Intelligence
stage need profiles/quality/leakage/readiness. These are a data concern, so a
**minimal, deterministic** `datasets/intelligence.py` provides them (extend, don't
rewrite, when authoritative V1-P3 lands). Placed in `datasets/` to respect
MODULE_BOUNDARIES; imports only `preprocessing` transitively.

### D6 — Certification is a real, qualified audit
Per the directive ("do NOT automatically certify"), `docs/certification/v1/`
contains a genuine audit. The verdict is **CERTIFIED (QUALIFIED)**: every
delivered-scope exit criterion passes and is reproducibly verified, but synthetic-
only data, the minimal V1-P1…P4 foundations, and unmechanized V0-P3 governance are
disclosed as gaps/risks and become **V2 blockers**. V2 is **not** auto-started
(NR-12); the `V2_READINESS_GATE.md` enumerates blockers and remediation.

## 3. Consequences

- The required deliverable runs end to end with full traceability:
  Dataset Ingestion → Validation → Preprocessing → Dataset Intelligence →
  Evaluation Preparation → Model Selection → Inference → Calibration → Conformal →
  Coverage → Risk → Output Generation → Artifact/Lineage/Audit Registration.
- The acyclic DAG is preserved and now enforced for **all six** domain modules,
  including `backend ↛ frontend` and `frontend ↛ {any domain}`.
- Every inference is registered, lineage-tracked, checksummed, validated, and
  reproducible; the offline app presents only registered artifacts.

## 4. Scope guard (explicitly NOT built — NR-13)

Real-time/streaming, multi-user, FHIR/EMR, hospital integration, alerting,
clinical deployment, and any V2/V3/V4 feature. The risk framework's
`operational_risk_hook` remains an inert forward seam (no operational logic).

## 5. Follow-ups / recorded debt (NR-2)

- Close certification Gaps G1–G4 (real-EEG validation; authoritative V1-P1…P4;
  mechanized V0-P3 governance) to upgrade the verdict to unqualified CERTIFIED.
- Replace the synthetic ingestion path with a real EEG file reader behind the
  `EEGDataset` contract.
- When V2 opens, the offline backend/frontend are **hardened** (APIs, audit trail,
  security) by extension — never re-layered (AP-1).
