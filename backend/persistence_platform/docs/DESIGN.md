# Persistence Platform — Design (DRP-4)

## Objective

Provide the durable persistence the audit found missing: persist registries, audit history,
lineage history, and execution history; recover them on a cold restart; validate the
recovery; and score persistence readiness. Strictly persistence — no model / training /
inference / serving / frontend / deployment / monitoring / security changes.

## Package layout

```
backend/persistence_platform/
  version.py            component versions + DETERMINISTIC_EPOCH
  models/domain.py      closed vocabularies + 13 records (DRP4-B)
  identity/             mints persistence_record / recovery_event; validates anchors
  storage/              StorageEngine — durable, content-addressed, tamper-evident (DRP4-C)
  repositories/         typed Repository over the engine (DRP4-D)
  registry_storage/     RegistryStore (DRP4-E)
  audit_storage/        AuditStore — persist + replay-recover audit chains (DRP4-F)
  lineage_storage/      LineageStore — persist + rebuild the shared lineage graph (DRP4-G)
  execution_storage/    ExecutionStore — persist + recover history streams (DRP4-H)
  lifecycle/            RecoveryEngine — cold-restart reconstruction + verify (DRP4-I)
  validation/           content validators + integrity validator (DRP4-J; ml.validation)
  readiness/            PersistenceReadinessEngine — 6 dimensions (DRP4-K)
  audit/                make_persistence_audit_log (shared ImmutableAuditLog) (DRP4-L)
  lineage/              persistence + recovery lineage helpers (shared ml.lineage) (DRP4-L)
  reports/              eight deterministic report builders (DRP4-M)
  schemas/contracts.py  entity contracts (DRP4-N)
  service.py            PersistencePlatformService — the governed orchestration hub
```

## Durable storage (DRP4-C)

Objects are serialized as **canonical JSON** under `<root>/<namespace>/<key>.json`, each with
a sha256 **checksum** (over the on-disk bytes — tamper detection) and a content **fingerprint**
(reproducibility). Reads verify the checksum. Files persist across process restarts, so a
fresh engine at the same root reads the same state (cold-restart recoverable).

## Reuse, not duplication (DRP4-L)

- The shared `ImmutableAuditLog` is **serialized** (events + head) and **recovered by replay**
  — reproducing the same head; no parallel audit system.
- The shared `ml.lineage.LineageTracker` is **serialized** (nodes + edges) and **rebuilt** —
  `verify_chain` holds after recovery; no parallel lineage system.
- Registries (DRP-1 dataset / DRP-2 model / DRP-3 serving) are persisted via their `to_dict()`.

## Cold-restart recovery (DRP4-I)

`persist()` writes a **manifest** (a storage index of every persisted object + the anchor +
the persistence lineage node id). A fresh `PersistencePlatformService` at the same root reads
the manifest, checksum-verifies every object, rebuilds registries / audit logs / lineage /
execution histories, re-verifies the audit chains + the lineage chain, and records a
`recovery_event` lineage node parented on the persisted `persistence_record` node.

## Lineage chain

```
persistence_record node parents the anchor (a served execution/response node)
recovery_event node parents the persistence_record node
```

`verify_chain(recovery_event)` reaches the patient, covering
Dataset → Model → Inference → Serving → Persistence Record → Recovery Event.

## Determinism

The snapshot fingerprint is computed over the **source** state (registry snapshots, audit
heads, lineage node ids, execution counts) — *before* minting — so the `persistence_id`,
the persistence lineage node, and the version do not form a cycle. Identical state reproduces
the same `persistence_id` + version. Storage uses canonical JSON (sorted keys); no wall-clock,
no randomness.

## Readiness criteria

`READY` ⇔ storage + registry + audit + lineage persistence exist ∧ recovery exists **and
succeeds** ∧ validation passes ∧ a readiness score exists. Otherwise `PARTIALLY_READY`
(score ≥ 0.5, validation ok) or `NOT_READY`.

## Out of scope (forbidden in DRP-4)

Frontend changes, model retraining, inference changes, serving changes, deployment changes,
monitoring changes, security changes, clinical validation, DRP-5+. Durable storage is
local-filesystem JSON — no cloud / database / deployment.
