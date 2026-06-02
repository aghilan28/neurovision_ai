# Model Provisioning (MP-1)

> **Deployment blocker eliminated:** a **fresh** NeuroVision deployment now provisions a usable
> model during startup, so it reaches `/readyz {"ready": true}` and the upload → analyze →
> predict workflow works **with no manual operator step**. This document is the single
> reference for that behaviour and contains the four guides the MP-1 directive requires:
>
> 1. [Model Provisioning Guide](#1-model-provisioning-guide)
> 2. [Startup Guide](#2-startup-guide)
> 3. [Recovery Guide](#3-recovery-guide)
> 4. [Operator Guide](#4-operator-guide)

MP-1 is **provisioning only**. It is explicitly *not* about model accuracy, retraining, model
architecture, optimization, clinical validation, or a Track-2 replacement. It introduces **no**
new model framework and changes no datasets, security, or deployment architecture — it reuses
the existing `ApplicationPlatformService.prepare_model` pipeline.

---

## Root cause (what was fixed)

The Repository Truth Audit established the single highest-value blocker:

```
build_application() lifespan ran _validate_startup() (read-only) but NEVER provisioned a model
  -> ApplicationPlatformService._model_info == {}  after startup
  -> /readyz reported ready from the startup report ALONE (a false positive: ready=true,
     model_prepared=false)
  -> POST /v1/uploads -> upload_and_analyze() -> `if not self._model_info: raise
     ApplicationPlatformError("no model prepared")` -> uncaught -> HTTP 500
```

**The fix:** the single authoritative startup lifespan now provisions a model (MP1-D), and
`/readyz` reports `ready` only when a model is actually available (MP1-E), eliminating both the
500 and the false-positive readiness.

---

## 1. Model Provisioning Guide

**How a model becomes available.** On startup the server calls
`backend.application_platform.provisioning.provision_model(service)`, which:

1. Checks whether the service already has a usable **inference context**
   (`service.backend.model_context`). If present, provisioning is a **no-op** (idempotent).
2. Otherwise generates a deterministic, **synthetic, patient-disjoint bootstrap cohort** —
   two EEG recordings written in-memory with **MNE** (a pinned runtime dependency that ships
   in the Docker image), in the supported **FIF** format. No committed dataset and no network
   are required.
3. Calls the existing `ApplicationPlatformService.prepare_model(cohort, architecture=EEGNET,
   dataset_key="nv-bootstrap", seed=7)` — the **reused** P1–P5 pipeline (ingest → process →
   features → train → register). This trains and registers exactly one model.

**Determinism.** The synthetic recordings use fixed seeds, a fixed `256 Hz` sampling rate, a
fixed 8-channel montage, a zero measurement date, and a length of `analysis_seconds + margin`.
Combined with the deterministic `prepare_model` (`seed=7`, `DETERMINISTIC_EPOCH`), provisioning
yields the **same `model_id` every time**. Re-running it (on a restart, or a second call) is
therefore safe and reconstructs the same model identity — there is no duplicate registration.

**What it is not.** The bootstrap model exists so the product is *immediately usable*; MP-1
makes no claim about its clinical accuracy. A real trained model (e.g. from Track-2) can be
adopted via the existing `ApplicationPlatformService.use_track2_model` / `set_model_context`
paths without changing anything here.

---

## 2. Startup Guide

**Single authoritative lifecycle.** Provisioning runs inside the one existing application
lifespan in `backend/application_platform/server/factory.py :: build_application`. There is no
parallel initialization path: `uvicorn backend.application_platform.server.app:app` and
`python -m backend.application_platform.server.app` both serve the same `app`, whose lifespan:

1. runs `_validate_startup(service)` (health / readiness / security / operations — read-only);
2. runs `provision_model(service)` (MP1-D) and folds the result into `app.state.startup_report`
   (`model_provisioned`, `model_id`, `provisioning_source`);
3. raises a clear, non-silent `RuntimeError` if startup validation fails (no partial start).

**Configuration (env, documented, no hidden config).**

| Env var | Default | Effect |
|---|---|---|
| `NV_PROVISION_MODEL` | `on` | Provision a model on startup. Set `0`/`false`/`no`/`off` to disable (e.g. when an external model context is injected before serving). |
| `NV_ANALYSIS_SECONDS` | `20.0` | Analysis window; the bootstrap recordings are generated to exceed it so the bounded segment is always satisfiable. |
| `NV_WORKSPACE_DIR` | unset | Enables durable persistence + recovery (see Recovery Guide). |

Startup is fast and deterministic (model provisioning completes in ~1 second on the bootstrap
cohort).

---

## 3. Recovery Guide

**How restart recovery works.** Two independent mechanisms combine so a restarted server is
immediately usable again, with **no manual intervention and no operator shell commands**:

- **Application state (DBE-4).** When `NV_WORKSPACE_DIR` is set, accepted analyses / uploads /
  reports / the duplicate index are persisted and **replayed on startup** (reusing the DRP-4
  `StorageEngine`). A previously-uploaded analysis is retrievable after restart.
- **Model availability (MP-1).** The inference *context* (`backend.model_context`) is process
  state and is **not** persisted; instead it is **re-provisioned on every startup**. Because
  provisioning is deterministic, the restarted server reconstructs the **identical `model_id`**
  it had before — so `model/status` and the persisted analyses' `model_info` snapshots remain
  consistent across the restart.

**Net effect:** `Upload → Predict → Report → Restart → Retrieve` works end-to-end, and a fresh
restart with an empty workspace is *also* immediately usable (the model is provisioned
regardless of whether any prior analysis exists).

---

## 4. Operator Guide

**Deploy and use — zero manual model steps.**

```bash
# Build + start the stack (compose); the backend provisions a model during startup.
docker compose -f operations/deployment/compose/docker-compose.yml up --build

# Wait for readiness (true ONLY when a model is available):
curl http://127.0.0.1:8000/readyz        # -> {"status":"ready","ready":true,"model_prepared":true}
curl http://127.0.0.1:8000/v1/model/status  # -> {"prepared":true,"model_id":"model+...","architecture":"eegnet",...}

# Use the product:
#   POST /v1/auth/register  -> POST /v1/auth/login  -> Bearer token
#   POST /v1/uploads        (EDF/EDF+/BDF/FIF/SET)  -> 201 + analysis_id
#   GET  /v1/analyses/{id}/prediction               -> 200
#   GET  /v1/analyses/{id}/reports                  -> 200
```

**Readiness contract (no false positives / negatives).**

| Condition | `/readyz` |
|---|---|
| Startup validated **and** a model is available | `{"ready": true, "model_prepared": true}` |
| Provisioning disabled (`NV_PROVISION_MODEL=0`) or no model yet | `{"ready": false, "model_prepared": false}` |

A load balancer / orchestrator that gates on `/readyz` will route traffic **only** when uploads
will actually succeed. (Note: the Docker `HEALTHCHECK` currently probes `/health`, i.e.
liveness; operators who want readiness-gated health may point it at `/readyz`.)

**Disabling provisioning.** Set `NV_PROVISION_MODEL=0` when you intend to inject a model
context out-of-band before serving traffic. While disabled and before a model is set, `/readyz`
honestly reports `ready=false` and `/v1/uploads` returns a controlled error rather than a 500
(authentication still hardened per DBE-5; the no-model business error is surfaced as a
controlled response by the API layer).

---

## Verifying

```bash
python -m scripts.verify_mp1_model_provisioning          # the 15 directive criteria
python -m pytest tests/test_mp1_model_provisioning.py    # the test suite
```
