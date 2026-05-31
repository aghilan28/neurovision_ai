# ADR-0027 — DRP-4: Persistence Platform

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Remediation Program DRP-4 (post-audit remediation)
> **Builds on:** ADR-0001 … ADR-0026 (Productization P1–P10 + DRP-1 + DRP-2 + DRP-3)
> **Resolves:** Audit blocker — *NO PERSISTENCE LAYER* (process-bound state; in-memory
> registries; non-durable serving / audit / lineage history)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse), AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty)

## 1. Context

After DRP-1 (datasets), DRP-2 (models), and DRP-3 (serving), the Independent Production
Reality Audit's next gap was that platform state was **process-bound**: registries were
in-memory and serving / audit / lineage history was not durable. DRP-4 adds the governed
persistence platform: durable storage, persistent registries, durable audit / lineage /
execution history, and cold-restart recovery. The scope is strictly persistence: no model /
training / inference / serving / frontend / deployment / monitoring / security changes (NR-13).

## 2. Decisions

### D1 — A new governed `backend/persistence_platform` subsystem
Adds the storage engine, repositories, registry/audit/lineage/execution stores, the recovery
engine, validation, readiness, reports, schemas, and a service hub. It persists + recovers
state; it modifies no business logic. As a `backend` package it obeys the import DAG (imports
`ml` + sibling `backend`, never `frontend`; enforced by `tests/test_boundaries.py`).

### D2 — Durable, content-addressed, tamper-evident filesystem storage
Objects are canonical-JSON files under `<root>/<namespace>/<key>.json` with a sha256 checksum
(tamper detection) + content fingerprint (reproducibility); reads verify the checksum. Files
persist across restarts (cold-restart recoverable). Local-filesystem only — no cloud / database
/ deployment (those are deployment concerns, out of scope).

### D3 — Reuse the shared audit + lineage; serialize and reconstruct (no parallel systems)
The shared `ImmutableAuditLog` is serialized (events + head) and **recovered by replay** —
reproducing the same head and re-verifying. The shared `ml.lineage.LineageTracker` is serialized
(nodes + edges) and **rebuilt** — `verify_chain` holds after recovery. The DRP-1/DRP-2/DRP-3
registries are persisted via their `to_dict()` snapshots.

### D4 — Cold-restart recovery via a manifest
`persist()` writes a manifest (a storage index of every persisted object + the anchor + the
persistence lineage node id). A fresh service at the same root reads it, checksum-verifies every
object, rebuilds registries / audit logs / lineage / execution histories, re-verifies the chains,
and records a `recovery_event` lineage node parented on the `persistence_record` node.

### D5 — Determinism without self-reference
The snapshot fingerprint is computed over the **source** state (registry snapshots, audit heads,
lineage node ids, execution counts) *before* minting — so the `persistence_id`, the persistence
lineage node (which embeds it), and the version do not form a cycle. Identical state reproduces
the same `persistence_id` + version; recovery is deterministic.

### D6 — Persistence readiness with a hard gate
Six weighted dimensions (storage / registry / recovery / audit / lineage / validation) → score
+ findings + NOT_READY / PARTIALLY_READY / READY. `READY` requires storage + registry + audit +
lineage persistence to exist, recovery to exist **and succeed**, validation to pass, and a
readiness score to exist.

## 3. Consequences

- `python -m scripts.verify_drp4_persistence_platform` → **ALL 15 CRITERIA PASS**; the platform
  state is persisted, recovered on a cold restart (checksum-verified), validated, scored
  **READY**, traceable (Dataset → Model → Inference → Serving → Persistence Record → Recovery
  Event), and audited. The verifier's determinism criterion is **stable** across repeated runs.
- The new suite adds 17 tests; the full repository suite is **908 passed** (was 891). `ruff`
  clean on all new code; `tests/test_boundaries.py` green; the suite's cross-run determinism
  test is stable (verified across repeated runs).
- No new runtime dependencies; the platform persists + recovers offline and deterministically.

## 4. Scope guard (explicitly NOT built — NR-13)

Frontend changes, model retraining, inference changes, serving changes, deployment changes,
monitoring changes, security changes, clinical validation, DRP-5+. No cloud / database / HA
persistence tier (deployment concerns).

## 5. Honesty statement (NR-2)

Durable storage is local-filesystem JSON — deterministic, checksummed, and restart-recoverable,
but not a distributed database or cloud object store (deployment concerns, out of scope). This
closes the *durability* blocker: registries, audit, lineage, and execution history now survive a
cold restart and are recovered + verified.

**Pre-existing, out-of-scope observation (disclosed, not fixed here):** the DRP-3 verification
script `scripts/verify_drp3_serving_platform.py` has a **flaky** cross-instance determinism
check (criterion 12) that intermittently fails — it reproduces on the clean DRP-3 branch with
the DRP-4 work removed, so it is **not** introduced by DRP-4. The DRP-3 *test suite's*
cross-run determinism test is stable, and serving ids are deterministic within a process; the
flake is isolated to that script's specific multi-architecture comparison. Fixing it would
require modifying serving / model-foundation code, which is **forbidden in DRP-4's scope**, so
it is recorded here for a later phase rather than changed.
