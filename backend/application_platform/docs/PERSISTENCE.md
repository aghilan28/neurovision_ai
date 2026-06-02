# Persistence, Recovery & Disaster Recovery (DBE-4)

This guide documents how NeuroVision application state survives an application **restart**.
The guarantee: an operator can upload an EEG, generate a prediction + report, **restart**
NeuroVision, and still retrieve the upload, prediction, and report — no state loss.

## Root cause (the bug this fixes)

The Final Hostile QA Audit found that application state (uploads, predictions, reports) lived
only in in-memory dicts on `ApplicationPlatformService`. A DRP-4 persistence platform existed
but was **not wired into the application lifecycle**, so a restart produced a fresh, empty
service and all state was lost.

## The fix (wiring, not a new database)

DBE-4 wires the application lifecycle to the **existing** DRP-4 `StorageEngine` (durable,
content-addressed, checksum-verified filesystem JSON) — no parallel persistence system, no new
database framework. On every accepted analysis the full `AnalysisOutcome` (+ report payloads +
duplicate-index entry + model snapshot) is serialized to durable JSON; on startup the store is
replayed to reconstruct the in-memory views and re-register the registry records.

## Storage location

* Configured by **`persistence_root`** (constructor) or the **`NV_PERSISTENCE_DIR`** env var.
* If neither is set, it derives from the workspace: **`<NV_WORKSPACE_DIR>/app_state`**.
* In the container (DBE-2), `NV_WORKSPACE_DIR=/var/lib/neurovision/workspace` is on the
  persistent `nv_data` volume, so `…/workspace/app_state` is durable across container restarts.
* If **no** workspace/persistence root is configured at all, the service runs **ephemeral**
  (historical behaviour) — state is not durable. Production always configures a workspace.

Layout: `<persistence_root>/app.analyses/<analysis_id>.json` — one durable record per accepted
analysis (atomic write; sha-256 checksum verified on read).

## Recovery process (automatic, no manual intervention)

Recovery runs **at service construction** (i.e. at server startup). It:
1. lists the durable analysis records,
2. reconstructs each `AnalysisOutcome` (via the domain `from_dict` methods),
3. repopulates the in-memory views (uploads / analyses / reports / duplicate index),
4. re-registers the registry records (registry stays consistent, no orphans),
5. restores the model snapshot used,
6. records a single `state_recovered` audit event.

A corrupt/unreadable record is **skipped** (logged in the recovery report's `errors`) — startup
never crashes. The recovery report is exposed at `GET /v1/persistence` and via
`service.recovery_report`.

## Restart behaviour

* **Normal shutdown** (SIGTERM via DBE-1 lifespan, or `docker stop`): durable records remain on
  disk; the next startup recovers them.
* **Unexpected shutdown** (kill -9 / crash): each record is written atomically (temp file +
  `os.replace`), so a record is either fully present or absent — never half-written. Already
  -persisted analyses recover; an analysis interrupted mid-flight simply was not persisted.
* **Repeated restart**: idempotent — recovery reproduces the same in-memory state and the same
  ids every time (determinism preserved).

## Retrieval after restart (API)

```bash
curl http://127.0.0.1:8000/v1/persistence                       # recovery status
curl http://127.0.0.1:8000/v1/analyses                          # list recovered analyses
curl http://127.0.0.1:8000/v1/uploads/<upload_id>               # recovered upload
curl http://127.0.0.1:8000/v1/analyses/<analysis_id>            # recovered analysis
curl http://127.0.0.1:8000/v1/analyses/<analysis_id>/prediction # recovered prediction + evidence
curl "http://127.0.0.1:8000/v1/analyses/<analysis_id>/reports?type=analysis&format=pdf"
```

All retrieval is served from persisted/recovered state (no live-workflow reconstruction).

## Operator guide

1. Run with a durable workspace (compose already mounts `nv_data` at `/var/lib/neurovision`):
   `docker compose -f operations/deployment/compose/docker-compose.yml up`.
2. Upload + predict + report (see `deployment/README.md`).
3. Restart: `docker compose restart backend` (or `down` then `up`).
4. Retrieve via the endpoints above — the analysis ids are unchanged.

## Disaster recovery guide

* The durable state is plain JSON files under `<persistence_root>/app.analyses/`. Back them up
  by snapshotting that directory (or the `nv_data` volume).
* To restore: point a new deployment's `NV_PERSISTENCE_DIR` (or `NV_WORKSPACE_DIR`) at the
  restored directory and start the server — recovery runs automatically on startup.
* Integrity: every record is checksum-verified on read; a tampered/corrupt file is skipped and
  surfaced in the recovery report rather than crashing startup.

## Scope (DBE-4)

Wires the existing persistence platform into the application lifecycle. It does not modify
datasets, models, inference, security, deployment/Docker, or token handling, and creates no new
database architecture.
