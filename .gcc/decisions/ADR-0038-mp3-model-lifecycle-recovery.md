# ADR-0038 — MP-3: Persistent Model Lifecycle & Recovery Certification

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Model Provisioning Program — MP-3
> **Builds on:** ADR-0001 … ADR-0037 (Productization + DRP + Tracks 1-4 + DBE-1…4 + MP-1 + Track-2 fix)
> **Resolves:** Model lifecycle durability — *a restart left the model in an unknown state; "recovery" was implicit and unverified, and readiness keyed on a snapshot (latent false positive)*
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse, no parallel systems), AP-9/NR-5 (this record),
> NR-13 (scope), NR-2 (honesty)

## 1. Context & root cause (audited from code)

MP-1 made a fresh deploy immediately usable by **provisioning** a deterministic model on
startup. But model "recovery" across a restart was only an *implicit side effect* of MP-1
provisioning's idempotency check, and the audit (ADR-0038 reality check) found four gaps:

- **GAP-1 (readiness false positive):** `/readyz` keyed `model_prepared` on the
  `service._model_info` **snapshot**, which DBE-4 recovery can restore *without* a usable
  inference context (`backend.model_context`) — so a restored snapshot could report `ready:true`
  with no servable model.
- **GAP-2:** `StartupReport.ok` excluded `model_provisioned`, so a restart where the snapshot was
  recovered but provisioning failed would not be caught.
- **GAP-3:** there was no explicit, observable model-recovery record and no verification that the
  re-provisioned model identity matched the prior one.
- **GAP-4:** the model identity was never persisted independently of an analysis, so continuity
  was *assumed from determinism*, never *verified*.

MP-3 resolves **only** model-lifecycle durability. Scope is strictly recovery + honest
readiness — no retraining, no new model framework/architecture, no dataset/security/operations/
deployment changes, and **no parallel recovery system**.

## 2. Decisions

### D1 — A single authoritative model-recovery step (MP3-D; `application_platform/lifecycle/`)
A new `lifecycle.recover_model(service)` is the one model-recovery path, run **inside the one
existing startup lifespan** (`server.factory.build_application`). It is **not** a parallel
system: it reuses the MP-1 `provision_model` (deterministic reconstruction → identical
`model_id`) and the DBE-4 `ApplicationStateStore`. It emits an observable `ModelRecoveryReport`
(stashed on `service._model_recovery`).

### D2 — Durable model identity, not weights (MP3-E)
`ApplicationStateStore` gains `persist_model_identity` / `load_model_identity` (+ a `health_ok`
round-trip probe) on the **same** `StorageEngine`, namespace `app.model`, key `provisioned`. It
persists the model `model_id` / `architecture` / `lineage_id` / `dataset_key` / `source` — **not
the weights** (the model is a deterministic reconstruction). `load_model_identity` never raises
(corrupt/absent → `None`). No new database, no parallel store.

### D3 — Verified identity continuity (MP3-E)
On recovery the freshly-available `model_id` is compared to the persisted one; a mismatch sets
`identity_continuous=False` and is surfaced as a finding (rather than assumed away). The model's
lineage node is recreated deterministically, so `verify_chain` from it still reaches the patient
and the shared audit chain still verifies — proving registry/lineage/audit survive the restart.

### D4 — Honest readiness keyed on the authoritative signal (MP3-G)
`/readyz` now keys `model_prepared` on `lifecycle.model_available` (= `backend.model_context is
not None`), and `ready` is derived via `assess_recovery_readiness`: true **only** when startup
validated **and** a usable model is available **and** identity is continuous **and** (if
configured) persistence is healthy. This closes GAP-1/2: a restored snapshot without a usable
context never reports ready, and a configured-but-unavailable persistence layer makes readiness
honestly `false`. Ephemeral mode (no persistence configured) remains valid (no false negative).

### D5 — Controlled failure recovery (MP3-F)
Normal/repeated/abrupt/interrupted restarts, persistence corruption, missing records, persistence
unavailability, and identity discontinuity all degrade in a controlled way — never a crash, never
a silent false positive. Atomic `StorageEngine` writes (temp + `os.replace`) mean an abrupt
shutdown leaves no half-written records.

### D6 — Determinism (NR-9/NR-10)
The model is reconstructed by the deterministic MP-1 bootstrap path, so the recovered `model_id`
equals the persisted one; the durable identity is canonical JSON (idempotent re-write). Repeated
restarts reproduce the same identity bit-for-bit.

## 3. Consequences

- `python -m scripts.verify_mp3_model_lifecycle` → **ALL 15 CRITERIA PASS**: lifecycle inventory,
  persistence + recovery audited, model/registry/metadata/audit/lineage/readiness survive restart,
  failure recovery validated, operator workflow validated, tests + boundaries green.
- New suite `tests/test_mp3_model_lifecycle.py` (15 tests) drives the real ASGI app + real store
  over temp workspaces (incl. genuine fault injection for the failure paths).
- `/v1/model/status` (+`recovery`) and `/v1/persistence` (+`model_recovery`) expose the report
  (additive; no contract break). MP-1 / DBE-4 / server verify scripts + suites remain green.
- `ruff` clean; `tests/test_boundaries.py` green; **no new dependencies**.

## 4. Scope guard (explicitly NOT done — NR-13)

Did not retrain models, change architecture, add a model framework, modify datasets, security,
operations, or deployment architecture, and created **no parallel recovery system** (the model
recovery reuses MP-1 provisioning + the DBE-4 StorageEngine inside the one startup lifecycle).
Model retirement/eviction remains an explicit non-goal.

## 5. Honesty statement (NR-2)

MP-3 makes the model lifecycle **durable across restarts** — verified by provisioning, restarting
a fresh service at the same workspace (a real cold restart), and proving the model is recovered
automatically with a **continuous identity** (identical `model_id`), valid registry/audit/lineage,
and honest readiness. The model itself is the deterministic MP-1 bootstrap reference model (no
clinical-accuracy claim); MP-3 persists and verifies its *identity*, not its weights, and does not
add distributed/cloud durability (a deployment concern, out of scope).
