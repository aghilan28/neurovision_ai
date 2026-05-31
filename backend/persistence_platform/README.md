# `backend/persistence_platform` — Persistence Platform (DRP-4)

Closes the audit's **no persistence layer** blocker: turns the in-memory platform into a
**persistent platform** with durable storage, persistent registries, and durable audit /
lineage / execution history that survives a cold restart. The scope is *persistence* and
nothing else — no model / training / inference / serving / frontend / deployment / monitoring
/ security changes (all explicitly out of scope).

Decision record:
[`../../.gcc/decisions/ADR-0027`](../../.gcc/decisions/ADR-0027-drp4-persistence-platform.md).

## What it does

```
persist registries + audit + lineage + execution -> write a recovery manifest ->
recover state (cold restart, checksum-verified) -> validate recovery -> score readiness ->
trace + audit
```

`PersistencePlatformService.persist(PlatformState)` durably persists a platform snapshot and
immediately verifies it by recovering from disk; `recover(persistence_id)` performs an explicit
cold-restart reconstruction from a fresh process/service.

## Durable storage (DRP4-C)

A deterministic, content-addressed, **tamper-evident** filesystem store: canonical-JSON objects
under `<root>/<namespace>/<key>.json`, each with a sha256 checksum + content fingerprint; reads
verify the checksum. Files persist across restarts (cold-restart recoverable). No cloud /
database / deployment.

## Reuse — no parallel systems (DRP4-L)

- **Audit:** the shared `ImmutableAuditLog` is serialized and **recovered by replay** — the
  recovered chain reproduces the same head and re-verifies (immutable history).
- **Lineage:** the shared `ml.lineage.LineageTracker` is serialized and **rebuilt** —
  `verify_chain` holds after recovery.
- **Registries:** the DRP-1 dataset, DRP-2 model, and DRP-3 serving registries are persisted
  via their `to_dict()` snapshots and reconstructed on recovery.

## Repositories (DRP4-D)

Typed, reusable repositories over the storage engine for datasets / models / training runs /
benchmarks / inference / serving / audit / lineage — storing already-serialized projections
(no duplicated business logic), reloadable by id with checksum verification.

## Cold-restart recovery (DRP4-I)

A fresh service at the same storage root reads a persisted **manifest**, checksum-verifies every
object, rebuilds registries + audit logs + lineage + execution histories, re-verifies the chains,
and records a `recovery_event` lineage node.

## Readiness (DRP4-K)

Six weighted dimensions — storage / registry / recovery / audit / lineage / validation. A
snapshot can be `READY` only when storage + registry + audit + lineage persistence exist,
recovery exists **and succeeds**, validation passes, and a readiness score exists; otherwise
`PARTIALLY_READY` or `NOT_READY`.

## Traceability (DRP4-L)

A single `verify_chain` from a recovery event reaches the patient:

```
Dataset -> Model -> Inference -> Serving -> Persistence Record -> Recovery Event
```

## Graceful failure

A corrupted or missing persisted object is **detected** (checksum mismatch / missing object) —
recovery degrades to `PARTIAL`/`FAILED` with structured findings, never a crash.

## Boundary (NR-8)

Imports `ml` + sibling `backend` only; never imports `frontend`. Deterministic throughout
(canonical JSON, no wall-clock, no randomness): identical state reproduces the same
`persistence_id` + version, and recovery is deterministic.

## Run

```bash
python -m scripts.verify_drp4_persistence_platform     # the 15 final-validation criteria
python -m pytest tests/test_persistence_platform.py tests/test_persistence_platform_e2e.py
```

## Honest scope

Durable storage is **local-filesystem JSON** — deterministic, checksummed, and restart-
recoverable, but not a distributed database, cloud object store, or HA persistence tier (those
are deployment concerns, out of scope / later phases). This closes the *durability* blocker:
registries, audit, lineage, and execution history now survive a cold restart and are recovered
+ verified.
