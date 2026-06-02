# Persistent Model Lifecycle & Recovery (MP-3)

> **Objective achieved:** a provisioned model now **survives the realities of deployment**.
> A restart no longer leaves the model in an unknown state — the single authoritative startup
> lifecycle **recovers the model automatically**, verifies its identity is continuous across
> the restart, and reports readiness honestly. This document is the single reference and
> contains both the **audit reports** (MP3-A/B/C) and the required **guides** (MP3-I):
>
> 1. [Lifecycle Inventory Report](#lifecycle-inventory-report) (MP3-A)
> 2. [Persistence Reality Report](#persistence-reality-report) (MP3-B)
> 3. [Recovery Reality Report](#recovery-reality-report) (MP3-C)
> 4. [Model Lifecycle Guide](#model-lifecycle-guide)
> 5. [Recovery Guide](#recovery-guide)
> 6. [Persistence Guide](#persistence-guide)
> 7. [Operator Restart Guide](#operator-restart-guide)
> 8. [Failure Recovery Guide](#failure-recovery-guide)

MP-3 is **operational durability only**. It is *not* about model training, accuracy, or
architecture. It introduces **no** new model framework and **no** parallel recovery system: it
reuses the **MP-1** provisioning path (deterministic reconstruction) and the **DBE-4**
`persistence_platform.StorageEngine`, and changes no datasets, security, operations, or
deployment architecture.

---

## Lifecycle Inventory Report

The model lifecycle, audited from code (not docs). Each stage lists its inputs, outputs,
dependencies, and failure points.

| Stage | Where | Inputs → Outputs | Failure points |
|---|---|---|---|
| **Model Creation** | `ApplicationPlatformService.prepare_model` → `application_backend.prepare_model` (P1→P4) | cohort files → trained `ModelRecord` + `backend.model_context` + `service._model_info` | cohort < 2 patients; unreadable EEG |
| **Model Registration** | `model_foundation` (shared `ModelRegistry`) + shared `ml.lineage` | `ModelRecord` → registered record + lineage node (`model_record.lineage_id`) | orphan record (guarded) |
| **Model Provisioning** | `provisioning.provision_model` (MP-1) | (none) → usable model from a deterministic synthetic FIF bootstrap cohort | provisioning disabled; numpy/mne missing |
| **Model Persistence** | `persistence.ApplicationStateStore` (DBE-4 + **MP-3**) | model **identity** → durable `app.model/provisioned.json` (NOT weights) | unwritable / corrupt store |
| **Model Recovery** | `lifecycle.recover_model` (**MP-3**) | durable identity + fresh provision → `ModelRecoveryReport` | identity discontinuity; persistence down |
| **Model Consumption** | `upload_and_analyze` → `backend.model_context` | upload → prediction + report | no usable model (gated) |
| **Model Retirement** | n/a | — | (no retirement/eviction concept; out of scope) |

**Authoritative usable-model signal:** `backend.model_context is not None`
(`lifecycle.model_available`). The lighter `service._model_info` dict is a *snapshot* only.

---

## Persistence Reality Report

**What survives a restart (durable):**

- **Application state (DBE-4):** every accepted analysis (`app.analyses/<id>.json`) with its
  upload / prediction / report payloads + duplicate index + an embedded `model_info` snapshot.
- **Model identity (MP-3, new):** the provisioned model's `model_id`, `architecture`,
  `lineage_id`, `dataset_key`, and `source` (`app.model/provisioned.json`) — written via the
  **same** `StorageEngine` (canonical JSON + sha256 checksum). **The model weights are *not*
  persisted by design** — the model is a deterministic reconstruction (see Recovery).

**What is *not* persisted (reconstructed instead):**

- The in-process inference context (`backend.model_context`), the `model_foundation`
  registry, and the shared lineage graph — all **rebuilt deterministically** by re-provisioning
  on startup, yielding the **identical** `model_id` and `lineage_id`.

**Why this is correct:** persisting model weights would add a parallel model store; instead
MP-3 persists the *identity* so recovery can **verify** that the deterministic reconstruction
reproduced the same model, rather than merely assuming determinism held.

---

## Recovery Reality Report

**Before MP-3:** model "recovery" was an *implicit side effect* of MP-1 provisioning's
idempotency check. There was no observable recovery record, the durable model identity was
never persisted independently of an analysis, identity continuity was never *verified*, and
`/readyz` keyed `model_prepared` on the `_model_info` **snapshot** — a latent false positive
(a restored snapshot could report "ready" with no usable inference context).

**After MP-3:** `lifecycle.recover_model` is the single authoritative recovery step run inside
the one existing startup lifespan. It (1) loads the durable prior identity, (2) ensures a
usable model via the reused MP-1 provisioner (deterministic → same `model_id`), (3) **verifies
identity continuity** (current `model_id` == persisted `model_id`), (4) re-persists the
identity for the next restart, (5) probes persistence health, and (6) emits a
`ModelRecoveryReport`. Readiness is then derived from the **authoritative** usable-model signal
plus recovery completeness — no false positives, no false negatives.

`verify_chain` from the recovered model's lineage node still reaches the patient; the shared
audit chain still verifies; the registry is orphan-free.

---

## Model Lifecycle Guide

A model becomes and stays available through these reused mechanisms:

1. **Provision (MP-1).** On startup `lifecycle.recover_model` calls `provision_model`, which —
   if no usable `backend.model_context` exists — generates a deterministic synthetic
   patient-disjoint FIF bootstrap cohort and runs the reused `prepare_model` (P1→P4). Same
   inputs ⇒ same `model_id` every run.
2. **Register.** The model is registered in `model_foundation` with a lineage node on the
   shared `ml.lineage` tracker; an audit `model_prepared` event is appended.
3. **Persist identity (MP-3).** The model identity (not weights) is written durably to
   `app.model/provisioned.json`.
4. **Consume.** `POST /v1/uploads` runs the workflow through `backend.model_context`.

The model is **immediately usable** and makes no clinical-accuracy claim (an MP-1 invariant
carried forward).

---

## Recovery Guide

**How a restart recovers the model — automatically, with no operator command:**

1. A fresh process constructs `ApplicationPlatformService`; DBE-4 replays persisted analyses.
2. The startup lifespan runs `lifecycle.recover_model`:
   - loads the durable model identity from `app.model/provisioned.json`;
   - re-provisions deterministically (the inference context is process state, so it is rebuilt
     — reconstructing the **identical** `model_id`);
   - **verifies** the reconstructed `model_id` equals the persisted one (continuity);
   - re-persists the identity and probes persistence health.
3. `/readyz` reports `ready:true` only when a usable model is available **and** identity is
   continuous **and** persistence (if configured) is healthy.

**Net effect:** `Upload → Predict → Report → Restart → Recover → Predict` works end-to-end with
no manual step. A brand-new restart with an empty workspace is *also* immediately usable.

---

## Persistence Guide

- Durable persistence activates when a workspace is configured (`NV_WORKSPACE_DIR`) or
  `NV_PERSISTENCE_DIR` is set; otherwise the server runs **ephemerally** (a valid historical
  mode — the model is still provisioned and the server is ready).
- The durable model identity lives at `<persistence_root>/app.model/provisioned.json`
  (canonical JSON, sha256-checksummed). It is **idempotent**: deterministic provisioning
  re-writes byte-identical content, so repeated restarts never duplicate or drift the record.
- **No model weights are stored** — only identity/metadata. There is no new database and no
  parallel store; everything reuses the DRP-4 `StorageEngine`.

| Env var | Default | Effect |
|---|---|---|
| `NV_PROVISION_MODEL` | `on` | Recover/provision a model on startup. `0`/`false` disables it (operator injects a context out-of-band); `/readyz` then honestly reports `ready:false` until a model is set. |
| `NV_WORKSPACE_DIR` | unset | Enables durable persistence + recovery (model identity + application state). |
| `NV_PERSISTENCE_DIR` | unset | Explicit persistence root (overrides the workspace default `<workspace>/app_state`). |

---

## Operator Restart Guide

Zero manual model steps — restart and keep serving:

```bash
# 1. Start (provisions + persists the model identity during startup)
NV_WORKSPACE_DIR=/var/lib/neurovision \
  uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8000

curl http://127.0.0.1:8000/readyz       # {"ready":true,"model_prepared":true,"model_recovered":true,"persistence_ok":true}

# 2. Use it: register -> login -> POST /v1/uploads -> GET /v1/analyses/{id}/prediction

# 3. Restart the SAME deployment (same NV_WORKSPACE_DIR)
#    -> the model is recovered automatically (identical model_id); prior analyses are retrievable
curl http://127.0.0.1:8000/readyz       # ready:true again, no manual step
curl http://127.0.0.1:8000/v1/model/status   # prepared:true + "recovery":{...,"recovered":true}
```

Inspect recovery details any time via `GET /v1/model/status` (`recovery` block) or
`GET /v1/persistence` (`model_recovery` block).

---

## Failure Recovery Guide

Every failure condition is **controlled** — no crash, no silent corruption, no false-positive
readiness.

| Condition | Behaviour |
|---|---|
| **Normal restart** | Recover automatically; identity continuous; `ready:true`. |
| **Repeated restart** | Deterministic + idempotent; the same `model_id` every time. |
| **Abrupt shutdown** | `StorageEngine` writes atomically (temp file + `os.replace`), so no half-written records; recovery proceeds. |
| **Interrupted / disabled provisioning** | `ready:false` honestly (no model); the server starts but routes no traffic via `/readyz`. |
| **Persistence corruption (identity)** | The corrupt durable identity is **tolerated** (treated as absent) and re-established from the freshly-provisioned model. |
| **Persistence unavailable** (unwritable/broken root) | `persistence_ok:false` → `ready:false` (honest); the model is still usable in-process, but durability is degraded, so traffic is withheld. |
| **Missing persisted record** | Treated as a fresh start (no prior identity); a model is provisioned and identity established. |
| **Registry / identity mismatch** | Identity discontinuity is **detected** (`identity_continuous:false`) → `ready:false`; re-registration is idempotent (no duplicate/orphan records). |

The `ModelRecoveryReport` (`GET /v1/persistence → model_recovery`) carries the exact findings
for each condition.

---

## Verifying

```bash
python -m scripts.verify_mp3_model_lifecycle          # the 15 directive criteria
python -m pytest tests/test_mp3_model_lifecycle.py    # the test suite
```
